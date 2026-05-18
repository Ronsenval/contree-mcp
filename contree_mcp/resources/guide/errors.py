"""
# Contree MCP — Failure Handling

Operations and commands can fail at two distinct layers. Check
them in order before deciding what went wrong.

## Layer 1: did the operation complete?

Inspect `status`:

| Status | Meaning | What to do |
|--------|---------|------------|
| `SUCCESS` | VM ran to completion (check exit_code next) | proceed to layer 2 |
| `FAILED` | VM-level error (image missing, OOM, scheduler) | read `error` field; usually not retryable as-is |
| `CANCELLED` | Manually cancelled or `wait_operations` timed out | retry with adjusted `timeout` if intentional |
| `EXECUTING` / `PENDING` | Still running | wait or `cancel_operation` |

`state: "SUCCESS"` does NOT mean the command succeeded — it means
the VM came up, ran something, and returned. The command's result
is in `exit_code`.

## Layer 2: did the command succeed?

Inspect `exit_code`:

    {
      "exit_code": 1,
      "state": "SUCCESS",
      "stdout": "",
      "stderr": "python: can't open file 'missing.py': [Errno 2]..."
    }

Common patterns:
  - `exit_code != 0`: read `stderr`; check the file/tool exists
    with `list_files` or `read_file` before re-running.
  - `timed_out: true`: command exceeded `timeout`. Raise it
    (server max 600s) or split the work into smaller `run`s.

## Image not found

`Image not found` / `tag not found`:

1. `list_images(tag_prefix="<prefix>")` to confirm what exists.
2. `import_image(registry_url="docker://...")` if it's a public
   image you haven't pulled yet.
3. Re-check the tag prefix: `tag:python:3.11` is correct;
   `python:3.11` alone (no `tag:`) is a UUID prefix.

## Directory state expired

`Directory state not found: ds_xxx`:

Directory state IDs do NOT persist across cache prunes.
Re-run `rsync` and pass the new `directory_state_id` immediately.

## Output truncated

`[TRUNCATED]` at the end of stdout / stderr:

- Raise `truncate_output_at` (default `8000`, server max 10 MiB).
- Redirect to a file inside the sandbox and `download` it:
    run(command="long-cmd > /tmp/out.log 2>&1",
        image="<uuid>", disposable=false)
    download(image="<result_image>", path="/tmp/out.log",
             destination="./out.log")
- Filter at the source: `... | head -100` / `... | tail -200`.

## Permission denied (403)

Call `whoami` to read the active permissions and limits:

    whoami()
    # -> {"permissions": {"import": true, "spawn": true,
    #                     "cancel": false, ...},
    #     "limits": {"instance_max_timeout": 3600,
    #                "instance_max_concurrency": 10, ...}}

If a permission is `false`, the only recourse is a token with
different grants — the MCP server cannot escalate.

## Operation cancelled by timeout

`wait_operations` returns before the operation finishes:
you hit the wait timeout, not the operation timeout. The op is
still running. Either:

  - `cancel_operation(operation_id=...)` to stop it, or
  - call `wait_operations(...)` again with a longer wait.

## Debugging loop

1. Read `state` and `exit_code` in that order.
2. Read `stderr` and any `error` field.
3. Verify inputs are real:
     - `list_images(tag_prefix=...)` for images
     - `list_files(image=..., path=...)` for paths
     - `whoami()` for permissions
4. Reproduce with a smaller `run` (lower `timeout`,
   `disposable=true`) before re-running the failing step.
5. Cross-reference recent activity:
     list_operations(status="FAILED", since="1h")
"""
