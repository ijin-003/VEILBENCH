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
from backend.mpc.exceptions import ConfigurationError, MPCTimeoutError, PartyDisconnectedError

logger = logging.getLogger("veilbench.mpc.distributed_coordinator")


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
    ) -> dict[str, Any]:
        try:
            response = await client.request(
                method,
                f"{self.party_urls[party_id]}{path}",
                headers=self._headers(party_id),
                timeout=self.timeout * 3 if compute_timeout else self.timeout,
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

    async def execute_protocol(self, session_id: str) -> dict[str, Any]:
        """Run the parties concurrently and return only the agreed aggregate."""
        async with self._client() as client:
            try:
                party_results = list(
                    await asyncio.gather(
                        *[
                            self._request(
                                client,
                                "POST",
                                party_id,
                                f"/sessions/{session_id}/compute",
                                compute_timeout=True,
                            )
                            for party_id in range(DEFAULT_PARTIES_COUNT)
                        ]
                    )
                )
                sums = [result["aggregate_sum"] for result in party_results]
                averages = [result["average_salary"] for result in party_results]
                for party_id, result in enumerate(party_results):
                    if (result.get("session_id") != session_id
                            or result.get("party_id") != party_id
                            or result.get("parties_count") != 3
                            or result.get("threshold") != 1):
                        raise ConfigurationError("Unexpected MPC result identity or parameters")
                if len(set(sums)) != 1 or len(set(averages)) != 1:
                    raise ConfigurationError("MPC parties returned inconsistent aggregate results")
                return {
                    "parties_count": DEFAULT_PARTIES_COUNT,
                    "aggregate_sum": sums[0],
                    "average_salary": averages[0],
                }
            finally:
                # Clear volatile inputs regardless of outcome. Cleanup errors
                # are logged but do not replace the original protocol failure.
                cleanup = await asyncio.gather(
                    *[
                        self._request(client, "POST", party_id, f"/sessions/{session_id}/shutdown")
                        for party_id in range(DEFAULT_PARTIES_COUNT)
                    ],
                    return_exceptions=True,
                )
                for party_id, result in enumerate(cleanup):
                    if isinstance(result, Exception):
                        logger.warning("Party %d did not confirm session cleanup", party_id)
