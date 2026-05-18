# Troubleshooting

Common issues and solutions.

## Connection Issues

### "No API token configured" Error

**Cause**: No active profile in `auth.ini` and no `--token` /
`CONTREE_TOKEN` override.

**Solution (recommended):** install `contree-cli` and run `contree auth`:

```bash
uv tool install contree-cli   # or: pip install contree-cli
contree auth                  # interactive setup
```

This writes `~/.config/contree/auth.ini`. The MCP server reads it
automatically.

For a one-off override:

```bash
export CONTREE_TOKEN="your-token"
export CONTREE_URL="https://api.tokenfactory.nebius.com/sandboxes"
export CONTREE_PROJECT="your-nebius-project-id"   # only for IAM auth
```

### Server logs `Ignoring NEBIUS_API_KEY: NEBIUS_AI_PROJECT is not set`

**Cause**: Your shell has `NEBIUS_API_KEY` set (typically for the
Nebius SDK or terraform provider) but no `NEBIUS_AI_PROJECT`. The MCP
server treats this as an incomplete IAM credential and falls back to
the active profile from `auth.ini`. This is *not* an error — it's a
deliberate guard against an ambient env var hijacking your saved
profile.

**Solution**: nothing to do if you wanted the profile to load. If you
*meant* to authenticate via env, also export `NEBIUS_AI_PROJECT` (or
use the MCP-specific `CONTREE_TOKEN` / `CONTREE_PROJECT`, which layer
per-field on top of the profile and don't have this guard).

### "IAM auth requires a project ID" Error

**Cause**: The active profile (or the env/CLI overrides) is IAM-typed
but no project ID was supplied.

**Solution**: either add `project = ...` under the matching
`[profile:<name>]` section, set `CONTREE_PROJECT`, or pass
`--project <id>`. For legacy JWT deployments, set `type = jwt` in the
profile — projects aren't needed there.

### "Connection refused" Error

**Cause**: Server not reachable or wrong URL.

**Solution**: Verify the URL in the active profile (or pass
`--url`/`CONTREE_URL`):

```bash
export CONTREE_URL="https://api.tokenfactory.nebius.com/sandboxes"
```

### "Forbidden" / Missing Permissions

**Cause**: The active token doesn't have the permission your call
needs (`spawn`, `import`, `set_image_tag`, `cancel`, ...).

**Solution**: ask the `whoami` tool to enumerate what's available:

```json
{"tool": "whoami"}
```

If a permission is `false`, the only recourse is a token with
different grants — the MCP server cannot escalate.

## Tool Errors

### "Image not found"

**Cause**: Invalid image UUID or tag.

**Solutions**:
1. Check with `list_images`
2. Ensure the UUID is correct
3. For tags, use `tag:` prefix: `"image": "tag:python:3.11"`

### "Directory state not found"

**Cause**: Invalid `directory_state_id` or expired session.

**Solution**: Call `rsync` again to get a new `directory_state_id`.

### "Operation timed out"

**Cause**: Command exceeded timeout.

**Solution**: Increase the timeout:

```json
{"tool": "run", "args": {
  "command": "...",
  "timeout": 600
}}
```

## Performance Issues

### Slow File Sync

**Cause**: Large files or too many files.

**Solutions**:
1. Use exclusions:
   ```json
   {"exclude": ["node_modules", ".git", "__pycache__", "*.log"]}
   ```
2. Sync only what you need
3. Use glob patterns for specific files

### Commands Taking Long to Start

**Cause**: VM startup time (~2-5 seconds).

**Solutions**:
1. Batch operations when possible
2. Use async for parallel operations
3. Reuse images with dependencies pre-installed

## Debugging

### Enable Debug Logging

Pass `--log-level debug` to the server:

```bash
contree-mcp --log-level debug ...
```

In an MCP client config that spawns the server, append the flag to
`args`:

```json
{
  "mcpServers": {
    "contree": {
      "command": "uvx",
      "args": ["contree-mcp", "--log-level", "debug"]
    }
  }
}
```

### Confirm the Installed Version

`contree-mcp --version` (or `-V`) prints the User-Agent the server
emits on every backend call. Useful when triaging which build is
actually wired into your client:

```bash
$ contree-mcp --version
contree-mcp/0.1.1 Python/3.13.0.final.0 Linux-6.5.0-arm64
```

### Check Operation Status

For async operations:

```json
{"tool": "get_operation", "args": {"operation_id": "op-..."}}
```

### View Image Lineage

To understand how an image was created:

```
contree://image/your-image-uuid/lineage
```

## Getting Help

- [GitHub Issues](https://github.com/nebius/contree/issues)
- Check the [Concepts](../concepts/index.md) for understanding
- See [Patterns](../patterns.md) for best practices
