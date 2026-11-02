from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_prefix="REGIONGATE_",
    )

    database_url: str = "sqlite+aiosqlite:///./regiongate.db"
    token_signing_key: str = "dev-only-change-me-32-bytes-key!!"
    config_signing_private_key: str = ""  # Ed25519 PEM or raw; empty = dev unsigned
    admin_bootstrap_password: str = "change-me-bootstrap"
    agent_socket: str = "/tmp/regiongate-agent.sock"
    api_origin: str = "http://localhost:8000"
    edge_host: str = "edge.example.com"
    edge_port: int = 443
    vpngate_feed_url: str = "https://www.vpngate.net/api/iphone/"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 30
    enrollment_code_ttl_minutes: int = 15
    rate_limit_login_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
