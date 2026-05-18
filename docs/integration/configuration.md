# Configuration

Detailed configuration options for Contree MCP.

## Authentication

### Profile File (Recommended)

`contree-mcp` reads the same profile file that
[`contree-cli`](https://docs.contree.dev/cli/tutorial/installation.html)
writes, so a single login covers both tools. Install the CLI and run
`contree auth`:

```bash
uv tool install contree-cli   # or: pip install contree-cli
contree auth                  # interactive setup
```

This writes `~/.config/contree/auth.ini` with mode `0600`. Override
the directory with `CONTREE_HOME`.

The file is INI-format with one `[profile:<name>]` section per
credential set and a `[DEFAULT] profile = <name>` line selecting the
active profile:

```ini
[DEFAULT]
profile = default

[profile:default]
type = iam
url = https://api.tokenfactory.nebius.com/sandboxes
token = <TOKEN HERE>
project = <NEBIUS PROJECT ID>

[profile:staging]
type = jwt
url = https://contree.dev
token = <TOKEN HERE>
```

Switch profiles persistently with `contree auth switch <name>`, or
per-invocation with `--profile <name>` / `CONTREE_PROFILE=<name>`.

`type = iam` requires `project`; `type = jwt` does not.

### Environment Variables (Per-Invocation Overrides)

For one-off overrides without touching the profile file:

```bash
export CONTREE_TOKEN="your-token-here"
export CONTREE_URL="https://api.tokenfactory.nebius.com/sandboxes"
export CONTREE_PROJECT="your-nebius-project-id"
```

Resolution priority is **CLI flag > env var > stored profile**.
Tokens passed via env may appear in process listings — prefer the
profile file for routine use.

## Server Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| - | `CONTREE_HOME` | `$XDG_CONFIG_HOME/contree` (typically `~/.config/contree`) | Directory containing `auth.ini` and MCP state |
| `--profile` | `CONTREE_PROFILE` | active profile from `auth.ini` | Profile to use |
| `--token` | `CONTREE_TOKEN` | from profile | API token (overrides profile) |
| `--url` | `CONTREE_URL` | from profile | API base URL (overrides profile) |
| `--project` | `CONTREE_PROJECT` | from profile | Project ID for IAM auth |
| `--mode` | - | `stdio` | `stdio` or `http` |
| `--http-port` | - | `9452` | HTTP mode port |
| `--http-listen` | - | `127.0.0.1` | HTTP mode bind address |
| `--log-level` | - | `warning` | Logging level |
| `--version` / `-V` | - | - | Print the User-Agent the server emits and exit |
| - | `CONTREE_NO_UPDATE_CHECK` | unset | Disable the daily PyPI update check (set to any value) |

## Cache Configuration

| Option | Default |
|--------|---------|
| `--cache-files` | `$CONTREE_HOME/mcp/files.db` (typically `~/.config/contree/mcp/files.db`) |
| `--cache-general` | `$CONTREE_HOME/mcp/cache.db` (typically `~/.config/contree/mcp/cache.db`) |
| `--cache-prune-days` | `60` |

## Client Configuration Examples

With credentials stored in `~/.config/contree/auth.ini`, MCP client
configs are minimal:

### Claude Code

```bash
claude mcp add --transport stdio contree -- $(which uvx) contree-mcp
```

### HTTP Mode

For network access from other machines:

```bash
contree-mcp --mode http --http-port 9452 --http-listen 0.0.0.0
```

Visit `http://localhost:9452/` for interactive documentation with setup guides, tool reference, and best practices.

```{figure} ../_static/http-index-page-screenshot.png
:alt: Contree MCP Server HTTP interface
:width: 100%

The HTTP interface showing Setup, Instructions, Tools, Resources, and Guides tabs.
```

## Manual Installation

```bash
# Using uv
uv pip install contree-mcp

# Using pip
pip install contree-mcp

# Container environments (PEP 668)
pip install --break-system-packages contree-mcp
```
