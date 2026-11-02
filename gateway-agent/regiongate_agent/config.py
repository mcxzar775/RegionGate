from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REGIONGATE_AGENT_", extra="ignore")

    dry_run: bool = True
    socket_path: str = "/tmp/regiongate-agent.sock"
    namespace_prefix: str = "rg-"
    openvpn_bin: str = "/usr/sbin/openvpn"
    ip_bin: str = "/usr/sbin/ip"
    allowed_uids: str = "0"


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
