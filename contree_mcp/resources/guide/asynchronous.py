"""
# Contree MCP — Async and Parallel Execution

Two modes, controlled by `wait`:

- **`wait=true`** (default) — block for the result. Sequential
  workflows. Most workflows live here.
- **`wait=false`** — return an `operation_id` immediately and
  keep running. Use for slow operations (large builds, image
  imports, test suites) and for fan-out.

## Detached (single op)

    run(command="make -C /work build", image="...", wait=false)
    # -> {"operation_id": "op-1"}

    get_operation(operation_id="op-1")
    # poll until "status" is terminal (SUCCESS / FAILED / CANCELLED)

## Fan-out + join

Launch N runs in parallel, then wait once:

    run(command="python exp1.py", image="...", wait=false)  # op-1
    run(command="python exp2.py", image="...", wait=false)  # op-2
    run(command="python exp3.py", image="...", wait=false)  # op-3

    wait_operations(operation_ids=["op-1", "op-2", "op-3"])
    # default mode="all": blocks until every op is terminal

For first-completion semantics (race the slowest, kill it,
pick the winner), use `mode="any"`:

    wait_operations(operation_ids=["op-1", "op-2", "op-3"],
                    mode="any")
    # -> {"results": {"op-1": {...}},
    #     "completed": ["op-1"],
    #     "pending": ["op-2", "op-3"]}

`wait_operations(mode="any")` is MCP-only; the CLI's
`contree session wait` always waits for all.

## Operation states

| Status | Meaning |
|--------|---------|
| `PENDING` | Queued, no VM allocated yet |
| `ASSIGNED` | A worker has accepted the operation |
| `EXECUTING` | The command is running |
| `SUCCESS` | Operation completed; check `exit_code` for command result |
| `FAILED` | Operation failed (VM-level error, not exit_code != 0) |
| `CANCELLED` | Cancelled via `cancel_operation` or `wait_operations` timeout |

Match the API enum — uppercase. `list_operations(status="SUCCESS")`
filters by these values.

## Listing and filtering operations

    list_operations(limit=100, status="EXECUTING")
    list_operations(kind="instance", since="1h")
    list_operations(kind="image_import", since="2024-01-01T00:00:00Z",
                    until="2024-02-01T00:00:00Z")

`since` / `until` accept ISO timestamps or interval strings
(`600s`, `15m`, `2h`, `3d`, `1w`).

Each summary now carries telemetry: `duration`, `image_size`,
`consumed_cpu`, `consumed_memory`, `image_uuid`,
`result_image_uuid`. Use them to spot expensive runs before
inspecting individually.

## Cancellation

    cancel_operation(operation_id="op-1")

Cancellation is best-effort. Already-terminal ops return their
current status unchanged.

## When NOT to use async

- Single quick command (`run` with default `wait=true` is fine).
- You need the `result_image` immediately to chain the next step
  (just wait — the latency saved isn't worth the bookkeeping).

## Tips

- Keep operation IDs in a list; pass them to `wait_operations`
  rather than polling each individually.
- Use `list_operations(status="EXECUTING")` to see what is
  currently consuming workers across the project.
- `cancel_operation` is cheap — cancel ops you no longer need
  rather than letting them run to completion.
"""
