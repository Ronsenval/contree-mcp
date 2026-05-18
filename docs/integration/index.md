# Integration

Setting up and configuring Contree MCP.

```{toctree}
:maxdepth: 1

configuration
troubleshooting
```

## Quick Setup

See the [Quickstart](../quickstart.md) for basic setup instructions.

## Configuration Options

Credentials live in a profile-based `auth.ini` shared with
[`contree-cli`](https://docs.contree.dev/cli/tutorial/installation.html);
install the CLI and run `contree auth` once to populate it. The MCP
server then reads the active profile automatically.

| Option | Environment Variable | Default |
|--------|---------------------|---------|
| - | `CONTREE_HOME` | `$XDG_CONFIG_HOME/contree` (typically `~/.config/contree`) |
| `--profile` | `CONTREE_PROFILE` | active profile from `auth.ini` |
| `--token` | `CONTREE_TOKEN` | from profile |
| `--url` | `CONTREE_URL` | from profile |
| `--project` | `CONTREE_PROJECT` | from profile (IAM auth only) |
| `--mode` | - | `stdio` |
| `--http-port` | - | `9452` |
| `--log-level` | - | `warning` |
| `--version` / `-V` | - | print User-Agent and exit |

Resolution priority for credentials: **CLI flag > environment variable
> stored profile**.

## Supported Clients

- Claude Code
- Claude Desktop
- OpenAI Codex CLI
- Any MCP-compatible client

## See Also

- {doc}`configuration` - Detailed config options
- {doc}`troubleshooting` - Common issues
