from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from open_targets_platform_mcp.types import TransportType


class Settings(BaseSettings):
    """Settings for the server.

    pydantic_settings automatically scans environmental variables and validates
    the provided values.
    """

    model_config = SettingsConfigDict(env_prefix="OTP_MCP_")

    api_endpoint: HttpUrl = HttpUrl("https://api.platform.opentargets.org/api/v4/graphql")
    api_call_timeout: int = 30
    server_name: str = "Model Context Protocol server for Open Targets Platform"
    transport: TransportType = TransportType.HTTP
    http_host: str = "localhost"
    http_port: int = 8000
    jq_enabled: bool = True


settings = Settings()
