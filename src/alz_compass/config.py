"""Operator configuration. Source origins cannot be set by tool callers."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .disease import DEFAULT_MANIFEST


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    alz_compass_data_mode: Literal["live", "snapshot"] = "live"
    alz_compass_manifest: Path = Path(__file__).resolve().parents[2] / DEFAULT_MANIFEST
    alz_compass_test_fault: Literal["", "upstream_error"] = ""
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    databricks_host: str = ""
    alz_compass_model: str = "models.ai.gpt-5-6-luna"
