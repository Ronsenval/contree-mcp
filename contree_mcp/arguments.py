from enum import Enum
from pathlib import Path

import argclass

from .client import MCP_USER_AGENT
from .config import CONTREE_HOME

# Co-locate MCP caches with auth.ini and the update-check state under
# ``$CONTREE_HOME/mcp/`` so a single directory holds everything the MCP
# server writes (and ``CONTREE_HOME`` can scope it for tests).
MCP_HOME = CONTREE_HOME / "mcp"


class ServerMode(str, Enum):
    STDIO = "stdio"
    HTTP = "http"


class HTTPGroup(argclass.Group):
    listen: str = argclass.Argument(default="127.0.0.1")
    port: int = argclass.Argument(default=9452)


class Cache(argclass.Group):
    files: Path = MCP_HOME / "files.db"
    general: Path = MCP_HOME / "cache.db"
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

    version = argclass.Argument(
        "-V",
        "--version",
        action=argclass.Actions.VERSION,
        version=MCP_USER_AGENT,
        help="Print the User-Agent string this server sends and exit",
    )

    log_level: int = argclass.LogLevel
    http: HTTPGroup = HTTPGroup()
    cache: Cache = Cache()
