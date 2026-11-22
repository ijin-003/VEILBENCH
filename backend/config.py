"""Application configuration.

Secrets deliberately have no development defaults. A service may expose the
health endpoint without them, but session creation and MPC orchestration fail
closed until the required values are configured.
"""

import json
import os
from pathlib import Path
from typing import List, Union
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "VEILBENCH"
    VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
    ]
    FRONTEND_PUBLIC_URL: str = "https://localhost:3000"

    # The protocol is intentionally fixed at three parties and t=1.
    MPC_THRESHOLD: int = 1
    MPC_PARTIES_COUNT: int = 3
    MPC_TIMEOUT_SECONDS: int = 30
    MPC_REQUIRE_TLS: bool = True
    MPC_NODE0_URL: str = "https://veilbench-mpc-node0:8100"
    MPC_NODE1_URL: str = "https://veilbench-mpc-node1:8100"
    MPC_NODE2_URL: str = "https://veilbench-mpc-node2:8100"
    MPC_NODE0_TOKEN: str = ""
    MPC_NODE1_TOKEN: str = ""
    MPC_NODE2_TOKEN: str = ""
    MPC_CA_CERT_PATH: str = ""
    MPC_CLIENT_CERT_PATH: str = ""
    MPC_CLIENT_KEY_PATH: str = ""
    MPC_PARTY_PUBLIC_URLS: Union[List[str], str] = [
        "https://localhost:8100",
        "https://localhost:8101",
        "https://localhost:8102",
    ]

    # Supplied through the environment or an untracked .env file only.
    COORDINATOR_ADMIN_TOKEN: str = ""
    MPC_FOUNDER_TOKEN_SECRET_0: str = ""
    MPC_FOUNDER_TOKEN_SECRET_1: str = ""
    MPC_FOUNDER_TOKEN_SECRET_2: str = ""
    SESSION_TTL_SECONDS: int = 1800

    # No shared hard-coded database password is used by default.
    DATABASE_URL: str = ""
    DATABASE_AUTO_CREATE: bool = True

    @field_validator("ALLOWED_ORIGINS", "MPC_PARTY_PUBLIC_URLS", mode="before")
    @classmethod
    def parse_list(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def party_urls(self) -> list[str]:
        return [self.MPC_NODE0_URL, self.MPC_NODE1_URL, self.MPC_NODE2_URL]

    @property
    def party_control_tokens(self) -> list[str]:
        return [self.MPC_NODE0_TOKEN, self.MPC_NODE1_TOKEN, self.MPC_NODE2_TOKEN]

    @property
    def founder_secrets(self) -> list[str]:
        return [self.MPC_FOUNDER_TOKEN_SECRET_0, self.MPC_FOUNDER_TOKEN_SECRET_1,
                self.MPC_FOUNDER_TOKEN_SECRET_2]

    def validate_production_configuration(self) -> None:
        """Reject unsafe or incomplete settings before a production process starts."""
        errors: list[str] = []
        try:
            self.validate_mpc_runtime()
        except RuntimeError as error:
            errors.append(str(error))

        if self.DEBUG:
            errors.append("DEBUG must be disabled in production")
        if self.DATABASE_AUTO_CREATE:
            errors.append("DATABASE_AUTO_CREATE must be disabled; apply Alembic migrations")
        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use postgresql+asyncpg in production")

        protected_values = [
            self.COORDINATOR_ADMIN_TOKEN,
            *self.party_control_tokens,
            *self.founder_secrets,
        ]
        if any(len(value) < 32 for value in protected_values):
            errors.append("All production admin, party-control, and founder-signing secrets must be at least 32 characters")
        if len(set(protected_values)) != len(protected_values):
            errors.append("Production admin, party-control, and founder-signing secrets must all be unique")

        if any(origin == "*" or not origin.startswith("https://") for origin in self.ALLOWED_ORIGINS):
            errors.append("ALLOWED_ORIGINS must contain only exact HTTPS origins in production")
        for origin in self.ALLOWED_ORIGINS:
            parsed_origin = urlsplit(origin)
            if (
                not parsed_origin.netloc
                or parsed_origin.path not in {"", "/"}
                or parsed_origin.query
                or parsed_origin.fragment
                or parsed_origin.hostname in {"localhost", "127.0.0.1", "::1"}
            ):
                errors.append("ALLOWED_ORIGINS entries must be public HTTPS origins without paths")
                break

        for url in self.MPC_PARTY_PUBLIC_URLS:
            parsed_url = urlsplit(url)
            if parsed_url.path not in {"", "/"} or parsed_url.query:
                errors.append("MPC_PARTY_PUBLIC_URLS entries must be base origins without paths or queries")
                break
            if parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}:
                errors.append("MPC_PARTY_PUBLIC_URLS must not use localhost in production")
                break

        for name, path in (
            ("MPC_CA_CERT_PATH", self.MPC_CA_CERT_PATH),
            ("MPC_CLIENT_CERT_PATH", self.MPC_CLIENT_CERT_PATH),
            ("MPC_CLIENT_KEY_PATH", self.MPC_CLIENT_KEY_PATH),
        ):
            if not path or not Path(path).is_file():
                errors.append(f"{name} must point to an existing readable file")
        if self.MPC_CLIENT_KEY_PATH and Path(self.MPC_CLIENT_KEY_PATH).is_file() and os.name == "posix":
            if Path(self.MPC_CLIENT_KEY_PATH).stat().st_mode & 0o077:
                errors.append("MPC_CLIENT_KEY_PATH must not be accessible by group or other users")

        if errors:
            raise RuntimeError("; ".join(errors))

    def validate_mpc_runtime(self) -> None:
        """Raise a safe configuration error before a session is created."""
        errors: list[str] = []
        if self.MPC_PARTIES_COUNT != 3 or self.MPC_THRESHOLD != 1:
            errors.append("VEILBENCH requires exactly three parties and threshold one")
        if not self.COORDINATOR_ADMIN_TOKEN:
            errors.append("COORDINATOR_ADMIN_TOKEN is not configured")
        if any(not secret for secret in self.founder_secrets) or len(set(self.founder_secrets)) != 3:
            errors.append("Three distinct founder signing secrets must be configured")
        if len(self.MPC_PARTY_PUBLIC_URLS) != 3:
            errors.append("MPC_PARTY_PUBLIC_URLS must contain exactly three URLs")
        else:
            normalized_party_urls = [url.rstrip("/").lower() for url in self.MPC_PARTY_PUBLIC_URLS]
            if len(set(normalized_party_urls)) != 3:
                errors.append("MPC_PARTY_PUBLIC_URLS must identify three distinct party endpoints")
            for url in self.MPC_PARTY_PUBLIC_URLS:
                parsed = urlsplit(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    errors.append("Every MPC_PARTY_PUBLIC_URLS entry must be an absolute HTTP(S) URL")
                    break
                if parsed.username or parsed.password or parsed.fragment:
                    errors.append("MPC party public URLs cannot contain credentials or fragments")
                    break
                if self.ENVIRONMENT.lower() == "production" and parsed.scheme != "https":
                    errors.append("MPC party public URLs must use HTTPS in production")
                    break

        frontend = urlsplit(self.FRONTEND_PUBLIC_URL)
        if frontend.scheme not in {"http", "https"} or not frontend.netloc:
            errors.append("FRONTEND_PUBLIC_URL must be an absolute HTTP(S) URL")
        elif frontend.username or frontend.password or frontend.query or frontend.fragment:
            errors.append("FRONTEND_PUBLIC_URL cannot contain credentials, query, or fragment")
        elif self.ENVIRONMENT.lower() == "production" and frontend.scheme != "https":
            errors.append("FRONTEND_PUBLIC_URL must use HTTPS in production")
        elif frontend.path not in {"", "/"}:
            errors.append("FRONTEND_PUBLIC_URL must be an origin without a path")

        if self.ENVIRONMENT.lower() == "production":
            if not self.MPC_REQUIRE_TLS:
                errors.append("MPC_REQUIRE_TLS must be enabled in production")
            frontend_origin = f"{frontend.scheme}://{frontend.netloc}" if frontend.netloc else ""
            if frontend_origin and frontend_origin not in self.ALLOWED_ORIGINS:
                errors.append("ALLOWED_ORIGINS must include FRONTEND_PUBLIC_URL")

        if any(not token for token in self.party_control_tokens):
            errors.append("all MPC_NODE*_TOKEN values must be configured")
        if self.MPC_REQUIRE_TLS:
            if any(not url.startswith("https://") for url in self.party_urls):
                errors.append("MPC node control URLs must use HTTPS")
            if not self.MPC_CA_CERT_PATH:
                errors.append("MPC_CA_CERT_PATH is not configured")
            if not self.MPC_CLIENT_CERT_PATH or not self.MPC_CLIENT_KEY_PATH:
                errors.append("MPC client certificate and key paths are not configured")
        if errors:
            raise RuntimeError("; ".join(errors))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
