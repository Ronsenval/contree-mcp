from contree_mcp.backend_types import WhoAmIResponse
from contree_mcp.context import CLIENT


async def whoami() -> WhoAmIResponse:
    """
    Introspect the current API token. Free (no VM).

    TL;DR:
    - PURPOSE: Find out which permissions and limits the current token has
    - COST: Free (no VM, single GET /whoami request)

    USAGE:
    - Call this when a tool fails with 403 to confirm which permissions are missing
    - Inspect ``limits`` (e.g. instance_max_timeout, instance_max_concurrency) before
      sending a large batch of operations
    - ``token_expiration`` is a Unix timestamp (or null) — warn the user before it lapses

    RETURNS:
    - token_uuid: UUID of the current token
    - token_expiration: Unix timestamp when the token expires, or null
    - permissions: map of permission name -> granted (bool)
    - limits: map of limit name -> integer value
    - operations_stat: per-token operation counters (may be empty)
    """
    client = CLIENT.get()
    return await client.whoami()
