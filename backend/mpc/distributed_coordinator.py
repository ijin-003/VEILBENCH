"""Coordinator for an already-submitted, distributed MPC session.

This module deliberately has no method accepting salaries. Founders submit
directly to their assigned party over HTTPS; the coordinator only polls
metadata and asks the three nodes to begin the MPyC protocol.
"""

import asyncio
import logging
import ssl
from pathlib import Path
from typing import Any

import httpx

from backend.mpc.config import DEFAULT_PARTIES_COUNT, MPC_TIMEOUT_SECONDS
from backend.mpc.exceptions import (
    ConfigurationError,
    MPCExecutionFailed,
    MPCRecoveryRequired,
    MPCTimeoutError,
    PartyDisconnectedError,
)

logger = logging.getLogger("veilbench.mpc.distributed_coordinator")
CLEANUP_ATTEMPTS = 3
CLEANUP_RETRY_DELAY_SECONDS = 0.25


class DistributedCoordinator:
    """Coordinate exactly three remote party services without handling inputs."""

    def __init__(
        self,
        party_urls: list[str],
        auth_tokens: list[str],
        *,
        ca_cert_path: str = "",
        client_cert_path: str = "",
        client_key_path: str = "",
        require_tls: bool = True,
        timeout: float = MPC_TIMEOUT_SECONDS,
    ) -> None:
        if len(party_urls) != DEFAULT_PARTIES_COUNT:
            raise ConfigurationError("VEILBENCH requires exactly three party URLs")
        if len(auth_tokens) != DEFAULT_PARTIES_COUNT or any(not token for token in auth_tokens):
            raise ConfigurationError("VEILBENCH requires three non-empty party control credentials")
        if require_tls and any(not url.startswith("https://") for url in party_urls):
            raise ConfigurationError("Party control URLs must use HTTPS")

        self.party_urls = [url.rstrip("/") for url in party_urls]
        self.auth_tokens = auth_tokens
        self.timeout = timeout
        self.require_tls = require_tls
        self._ssl_context: ssl.SSLContext | bool
        if require_tls:
            if not ca_cert_path or not client_cert_path or not client_key_path:
                raise ConfigurationError("CA and coordinator client certificates are required for TLS")
            for path in (ca_cert_path, client_cert_path, client_key_path):
                if not Path(path).is_file():
                    raise ConfigurationError("A configured MPC TLS certificate file is missing")
            context = ssl.create_default_context(cafile=ca_cert_path)
            context.load_cert_chain(client_cert_path, client_key_path)
            self._ssl_context = context
        else:
            # Plain HTTP is allowed only for isolated unit tests and explicit
            # local development, never by the application session API.
            self._ssl_context = False

    def _headers(self, party_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth_tokens[party_id]}"}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self._ssl_context, timeout=self.timeout)

    async def _request(
        self,
        client: httpx.AsyncClient,
        method: str,
        party_id: int,
        path: str,
        *,
        compute_timeout: bool = False,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await client.request(
                method,
                f"{self.party_urls[party_id]}{path}",
                headers=self._headers(party_id),
                timeout=self.timeout * 3 if compute_timeout else self.timeout,
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as error:
            raise MPCTimeoutError(f"Party {party_id} did not respond in time") from error
        except httpx.HTTPStatusError as error:
            # Do not include party response text: it may contain deployment
            # details and is not useful to API callers.
            raise PartyDisconnectedError(
                f"Party {party_id} rejected the coordinator request (HTTP {error.response.status_code})"
            ) from error
        except httpx.HTTPError as error:
            raise PartyDisconnectedError(f"Party {party_id} could not be reached") from error

    async def get_statuses(self, session_id: str) -> list[dict[str, Any]]:
        async with self._client() as client:
            return list(
                await asyncio.gather(
                    *[
                        self._request(client, "GET", party_id, f"/sessions/{session_id}/status")
                        for party_id in range(DEFAULT_PARTIES_COUNT)
                    ]
                )
            )

    async def _cleanup_party_sessions(
        self,
        client: httpx.AsyncClient,
        session_id: str,
        expires_at: int | None,
    ) -> None:
        """Retry idempotent shutdown until every party confirms its tombstone."""
        pending = set(range(DEFAULT_PARTIES_COUNT))
        last_errors: dict[int, Exception] = {}
        params = {"expires_at": expires_at} if expires_at is not None else None

        for attempt in range(CLEANUP_ATTEMPTS):
            results = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "POST",
                        party_id,
                        f"/sessions/{session_id}/shutdown",
                        params=params,
                    )
                    for party_id in sorted(pending)
                ],
                return_exceptions=True,
            )
            for party_id, result in zip(sorted(pending), results):
                if isinstance(result, BaseException):
                    if isinstance(result, Exception):
                        last_errors[party_id] = result
                else:
                    pending.discard(party_id)
                    last_errors.pop(party_id, None)

            if not pending:
                return
            if attempt + 1 < CLEANUP_ATTEMPTS:
                await asyncio.sleep(CLEANUP_RETRY_DELAY_SECONDS * (attempt + 1))

        logger.error(
            "Could not confirm MPC session cleanup for session %s; parties=%s",
            session_id,
            sorted(pending),
        )
        raise MPCRecoveryRequired(
            f"MPC party cleanup could not be confirmed for parties {sorted(pending)}"
        ) from next(iter(last_errors.values()), None)

    async def shutdown_session(self, session_id: str, expires_at: int | None = None) -> None:
        """Retry cleanup independently, including after a coordinator restart."""
        async with self._client() as client:
            await self._cleanup_party_sessions(client, session_id, expires_at)

    async def execute_protocol(
        self, session_id: str, expires_at: int | None = None
    ) -> dict[str, Any]:
        """Run parties concurrently, confirm cleanup, and return only the aggregate."""
        protocol_error: BaseException | None = None
        aggregate: dict[str, Any] | None = None

        async with self._client() as client:
            try:
                results = await asyncio.gather(
                    *[
                        self._request(
                            client,
                            "POST",
                            party_id,
                            f"/sessions/{session_id}/compute",
                            compute_timeout=True,
                        )
                        for party_id in range(DEFAULT_PARTIES_COUNT)
                    ],
                    return_exceptions=True,
                )
                failures = [item for item in results if isinstance(item, BaseException)]
                if failures:
                    protocol_error = failures[0]
                else:
                    party_results = list(results)
                    try:
                        sums = [result["aggregate_sum"] for result in party_results]
                        averages = [result["average_salary"] for result in party_results]
                        for party_id, result in enumerate(party_results):
                            if (
                                result.get("session_id") != session_id
                                or result.get("party_id") != party_id
                                or result.get("parties_count") != DEFAULT_PARTIES_COUNT
                                or result.get("threshold") != 1
                            ):
                                raise ConfigurationError(
                                    "Unexpected MPC result identity or parameters"
                                )
                        if len(set(sums)) != 1 or len(set(averages)) != 1:
                            raise ConfigurationError(
                                "MPC parties returned inconsistent aggregate results"
                            )
                        aggregate = {
                            "parties_count": DEFAULT_PARTIES_COUNT,
                            "aggregate_sum": sums[0],
                            "average_salary": averages[0],
                        }
                    except (KeyError, TypeError, ValueError, ConfigurationError) as error:
                        protocol_error = error
            except BaseException as error:
                protocol_error = error

            # Do not start cleanup until every compute request has settled. This
            # prevents a fast failure from racing shutdown against other parties
            # that are still running their MPyC subprocesses.
            try:
                await self._cleanup_party_sessions(client, session_id, expires_at)
            except MPCRecoveryRequired:
                raise

        if protocol_error is not None:
            if isinstance(protocol_error, asyncio.CancelledError):
                raise protocol_error
            raise MPCExecutionFailed(
                "MPC computation failed; all parties confirmed session cleanup"
            ) from protocol_error
        if aggregate is None:
            raise MPCExecutionFailed("MPC computation returned no aggregate result")
        return aggregate
