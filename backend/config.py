"""Application configuration.

Secrets deliberately have no development defaults. A service may expose the
health endpoint without them, but session creation and MPC orchestration fail
closed until the required values are configured.
"""

import json
from typing import List, Union

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
