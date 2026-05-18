# Contree MCP Server — QA Report

- **Date:** 2026-05-18 (initial audit & fix); re-verified 2026-05-18 after fix.
- **Branch:** `fetaure/contree-ini-config`
- **Scope:** Live exercise of every tool exposed by the Contree MCP server against the production backend, using the local MCP client.
- **Method:** One representative invocation per tool (more for `run`, which has the most surface). Free-cost (no-VM) tools first, then VM execution paths, then async/cancel paths, then state-mutating paths. `import_image` and registry auth tools were deliberately skipped (see below).

## Summary

- **Verified working:** 19 tool paths (17 in the initial audit + `upload`/`rsync` after the fix).
- **Initially broken, now fixed:** `upload` and `rsync` — single client-side bug (wrong URL + brittle response model). Patched in `contree_mcp/client.py` and `contree_mcp/backend_types.py`; verified live after MCP-server restart.
- **Not exercised:** `import_image`, `registry_auth`, `registry_token_obtain`.

The break was small in code but large in blast radius: every workflow that injects local files into a container goes through `upload`/`rsync`, so the second half of the documented quickstart pattern (file sync → execute) was inoperative until the fix.

## Environment

- Token UUID `dcc8b619-bf48-51b3-953d-6bd4bda94162`, expires `1779118677`.
- Permissions: `import`, `spawn`, `spawn_disposable`, `list`, `cancel`, `set_image_tag` — all granted.
- Limits: `instance_max_timeout=3600`, `instance_max_concurrency=10`, `instance_max_layer_bytes=12 GiB`, `images_import_max_concurrency=5`, `images_import_max_timeout=3600`.
- Test image: `tag:alpine:latest` (Alpine 3.23.3, UUID `eb1ea259-fac9-3a79-9ffd-487bbe34f7e0`).

## Results

### Free (no-VM) tools

| Tool | Status | Notes |
|---|---|---|
| `whoami` | PASS | Returned token UUID, permissions, limits, operations_stat. |
| `list_images` | PASS | Returned 20 images with UUIDs, tags, timestamps. |
| `get_image` | PASS | Resolved `tag:alpine:latest` → UUID. |
| `list_files` | PASS | Listed `/etc` (35 entries) with types, sizes, modes, symlink targets. |
| `read_file` | PASS | Returned `/etc/os-release` content + encoding + byte size. |
| `get_guide` | PASS | Returned `workflow` section; advertised sections: `async, errors, quickstart, reference, state, tagging, workflow`. |
| `list_operations` | PASS | Returned recent operations with status, duration, image UUIDs. |

### VM execution

| Scenario | Status | Notes |
|---|---|---|
| Basic disposable `run` | PASS | stdout, stderr, exit_code, resource metrics all captured. |
| `run` with `disposable=false` | PASS | Returned `result_image` UUID for chaining. |
| `run` with `env`, `stdin`, `cwd`, `uid`, `gid` | PASS | All parameters honored. Output confirmed `uid=1000 gid=1000`, `cwd=/etc`, env vars set, stdin piped to `cat`. |
| `run` with `wait=false` | PASS | Returned `operation_id` immediately. |

### Async / operations

| Tool | Status | Notes |
|---|---|---|
| `get_operation` | PASS | Observed `EXECUTING` state on a long-running op, then `CANCELLED` after cancel. |
| `wait_operations` | PASS | Blocked until the fast op completed; returned the full result inline. |
| `cancel_operation` | PASS | Cancelled the long-running op; subsequent `get_operation` returned `CANCELLED`. |

### State mutation

| Tool | Status | Notes |
|---|---|---|
| `set_tag` (assign) | PASS | Tagged result image as `myproject/feature-check/alpine:latest`. Subsequent `run` against the tag worked. |
| `set_tag` (remove) | PASS | Calling `set_tag` with `tag=null` cleared the tag. |
| `download` | PASS | Extracted `/payload/persisted.txt` (18 bytes) from result image; local content matched. |

### File injection — was BROKEN, now FIXED

| Tool | Initial | After fix | Notes |
|---|---|---|---|
| `upload` | FAIL | PASS | First upload returns `{uuid, sha256, size, …}`; second upload of identical content returns the same `uuid` (cache path no longer throws). |
| `rsync` | FAIL | PASS | Returned `directory_state_id=1`; subsequent `run(directory_state_id=1)` injected all three local files into `/work` with matching contents. |

Originally reproduced error (kept for the record):

```
Error executing tool upload: Streaming response: invalid JSON: 2 validation errors for FileResponse
uuid
  Field required [type=missing, input_value={'files': [{'uuid': 'ea35...-18T09:16:55.185199Z'}]}, input_type=dict]
sha256
  Field required [type=missing, input_value={'files': [{'uuid': 'ea35...-18T09:16:55.185199Z'}]}, input_type=dict]
```

Post-fix live verification (against the patched + restarted MCP):

- `upload(content="verify-upload-after-fix\nline2\n")` → `{"uuid":"bf0a3a75-…","sha256":"4cf29774…", …}`
- Re-upload of identical content → identical uuid + sha256, no error.
- `rsync(source="/tmp/contree-check", destination="/work")` → `{"result": 1}` (directory_state_id).
- `run(image=tag:alpine:latest, directory_state_id=1, command="ls -la /work && cat /work/a.txt && cat /work/b.txt")` → exit 0, `a.txt` = `"hello\nfrom rsync\n"`, `b.txt` = `"second file\n"`, both matching the local source.

### Not exercised

| Tool | Reason |
|---|---|
| `import_image` | Most expensive operation (can take dozens of minutes); the workflow guide explicitly flags it as a last resort. The local registry already has the images needed for this audit. |
| `registry_token_obtain` | Requires interactive PAT creation in a browser. |
| `registry_auth` | Depends on a token produced by `registry_token_obtain`. |

## Bug detail — `get_file_by_hash` used the wrong endpoint contract (now fixed)

- **Location (pre-fix):** `contree_mcp/client.py:527` (plus the same wrong-URL pattern at `client.py:498` and `client.py:510`).
- **Affected tools:** `upload`, `rsync` (and any future tool that resolves a file by content hash).

### What the client does

`upload_file` (`client.py:455`) computes the SHA256 of the payload and calls `get_file_by_hash(sha256)` (`client.py:518`) before uploading, to deduplicate. That helper issues:

```python
response = await self._request("GET", "/files", model=FileResponse, params={"sha256": sha256})
```

The model `FileResponse` is declared at `contree_mcp/backend_types.py:97` and is a flat shape:

```python
class FileResponse(BaseModel):
    uuid: str
    sha256: str
    size: int = -1
    created_at: str | None = None
    updated_at: str | None = None
```

### What the server returns

From the error payload, the server response is list-shaped:

```json
{"files": [{"uuid": "ea35…", …, "created_at": "2026-05-18T09:16:55.185199Z"}]}
```

This matches the existing memory note about `GET /files` being a listing endpoint that needs source-mapping work before being exposed as a tool. The query-string form of `GET /files` is the *listing* endpoint, not the single-file fetch.

### What the docstring says

`backend_types.py:101-102` documents the contract as:

```
- POST /files -> FileResponse (uuid, sha256, size required)
- GET /files/{sha256} -> File (uuid, sha256, size, created_at, updated_at required)
```

The single-file fetch is `GET /files/{sha256}` (path-style), not `GET /files?sha256=...` (query-style). The client is hitting the wrong URL.

### Applied fix

Option 1 was chosen (smaller diff, matches the existing docstring), plus a second layer of resilience on the response model so additive backend changes can no longer break the client.

**`contree_mcp/client.py`** — three call sites:

- `get_file_by_hash`: `GET /files?sha256=…` → `GET /files/{sha256}`.
- `check_file_exists_by_hash`: `HEAD /files?sha256=…` → `HEAD /files/{sha256}`.
- `check_file_exists` (by UUID): deleted entirely — no by-UUID endpoint exists on the server (the prior `HEAD /files?uuid=…` always returned 405, silently swallowed by `except Exception`). The function had no production callers, only tests.

**`contree_mcp/backend_types.py`** — `FileResponse` made permissive:

- `sha256` is now optional (`default=""`). The client only uses it for logging; `uuid` is the sole load-bearing field.
- A `model_validator(mode="before")` now unwraps two common envelope shapes — list-style `{"files": [item, …]}` and single-key `{"file": item}` — so the client survives backend response-shape drift. Same pattern already in use for `OperationListResponse.wrap_list`.
- Pydantic v2 `BaseModel` default `extra="ignore"` already silently accepts additive fields; this is now exercised by a regression test.

**Tests** (`tests/test_client.py`):

- 5 fake-response paths updated from `GET /files` / `HEAD /files` to `GET /files/{sha256}` / `HEAD /files/{sha256}`.
- 3 dead tests for `check_file_exists` (by UUID) removed.
- 2 regression tests added: list-envelope unwrapping and tolerance of unknown additive fields.

### Verification results (post-fix, live)

| Step | Expected | Actual |
|---|---|---|
| `upload(content="verify-upload-after-fix\nline2\n")` | Returns `uuid` + `sha256` | `uuid=bf0a3a75-…`, `sha256=4cf29774…` ✅ |
| Re-upload identical content | Cache path returns same uuid, no error | Same uuid+sha256, no error ✅ |
| `rsync` `/tmp/contree-check` → `/work` | Returns `directory_state_id` | `{"result": 1}` ✅ |
| `run(image=tag:alpine:latest, directory_state_id=1, command="ls -la /work && cat …")` | All local files present with matching contents | `a.txt`, `b.txt`, `persisted-downloaded.txt` all injected; contents match ✅ |
| `make test` on file-related suites (`test_client.py`, `test_file_cache.py`, `tests/tools/test_upload.py`, `tests/tools/test_rsync.py`) | All pass | 115 passed ✅ |
| `make lint typecheck` | Clean | `ruff check` + `mypy` clean ✅ |

## Reproduction commands

The exact MCP tool calls used during this audit (Alpine, free-tool surface, VM surface, async surface, file-injection surface) are reproducible from a single MCP session. The two initially-failing calls (now passing after the patch + MCP-server restart):

```jsonc
// upload — was FAIL, now PASS
{ "content": "verify-upload-after-fix\nline2\n" }

// rsync — was FAIL, now PASS
{ "source": "/tmp/contree-check", "destination": "/work" }
```

All other tool calls succeeded with the parameters listed in the Results section.
