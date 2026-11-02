"""Agent settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    agent_socket: str = "/run/regiongate/agent.sock"
    dry_run: bool = True
    namespace_prefix: str = "rg-"
    allowed_commands: list[str] = ["ip", "iptables", "openvpn", "curl"]

    class Config:
        env_prefix = "REGIONGATE_"


def get_settings() -> Settings:
    return Settings()
