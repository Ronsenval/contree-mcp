from enum import Enum
from pathlib import Path

import argclass


class ServerMode(str, Enum):
    STDIO = "stdio"
    HTTP = "http"


class HTTPGroup(argclass.Group):
    listen: str = argclass.Argument(default="127.0.0.1")
    port: int = argclass.Argument(default=9452)


class Cache(argclass.Group):
    files: Path = Path("~") / ".cache" / "contree_mcp" / "files.db"
    general: Path = Path("~") / ".cache" / "contree_mcp" / "cache.db"
    prune_days: int = argclass.Argument(
        default=60,
        help="Delete cached entries older than this many days",
    )


class Parser(argclass.Parser):
    profile: str | None = argclass.Argument(
        default=None,
        env_var="CONTREE_PROFILE",
        help="Config profile to use (default: active profile from config file)",
    )
    url: str | None = argclass.Argument(
        default=None,
        env_var="CONTREE_URL",
        help="Contree API base URL (overrides config and env)",
    )
    token: str | None = argclass.Argument(
        default=None,
        secret=True,
        env_var="CONTREE_TOKEN",
        help="Contree API authentication token (overrides config and env)",
    )
    project: str | None = argclass.Argument(
        default=None,
        env_var="CONTREE_PROJECT",
        help="Project ID for IAM authentication (overrides config and env)",
    )
    mode: ServerMode = argclass.EnumArgument(
        ServerMode, default=ServerMode.STDIO, lowercase=True, help="Server transport mode"
    )

    log_level: int = argclass.LogLevel
    http: HTTPGroup = HTTPGroup()
    cache: Cache = Cache()
