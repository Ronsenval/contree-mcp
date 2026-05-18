"""
# Contree MCP — State, Lineage, and Rollback

The MCP server is stateless: there are no `-S <key>` sessions and
no `session branch / checkout / rollback`. The durable state is the
set of image UUIDs and the lineage between them.

## Immutable snapshots

Every image UUID is an immutable filesystem snapshot. The same UUID
always represents the exact same state. Modifying behaviour for an
existing UUID is impossible — any "change" creates a new UUID.

## disposable controls whether a UUID is produced

| `disposable` | Behaviour | When |
|--------------|-----------|------|
| `true` (default) | Filesystem changes discarded; no new UUID | Read-only checks, tests, exploration |
| `false` | Changes persisted; `result_image` is a new UUID | Installs, builds, anything you want to chain |

**CLI users:** `contree run` defaults to non-disposable. The MCP
`run` tool defaults to **disposable**. Opt into `disposable=false`
explicitly when you want to keep the result.

## Lineage example

    run(command="pip install flask", image="tag:python:3.11",
        disposable=false)          -> result_image "A"

    run(command="pip install sqlalchemy", image="A",
        disposable=false)          -> result_image "B"

    run(command="pip install redis", image="A",
        disposable=false)          -> result_image "C"

    # A is the parent of both B and C. Both are reachable forever.

Inspect this graph for any image:

    ResourceTemplate: contree://image/{uuid}/lineage

Returns `parent`, `ancestors[]`, `children[]`, `root`, and
`depth` — useful for finding where to branch from or rolling back
to a known-good state.

## "Rollback" without a session

There is no `session rollback N`. Instead:

- To **undo the last step**, ignore the new UUID and reuse the
  previous `result_image` UUID in your next `run`.
- To **branch**, feed an earlier `result_image` UUID to a new
  `run` — the side effects of the abandoned branch don't reach
  your new path.
- To **persist** a known-good state, `set_tag` it so the UUID
  doesn't have to be remembered.

## Tag conventions and image discovery

Use `list_images(tag_prefix=...)` to find prior work; see
contree://guide/tagging for the naming convention. Without tags,
UUIDs are only reachable from operations you still remember.

## Response shape (disposable=false)

    {
      "exit_code": 0,
      "state": "SUCCESS",
      "result_image": "uuid-new",
      "filesystem_changed": true,
      "stdout": "Successfully installed numpy-1.24.0",
      "stderr": ""
    }

`state: "SUCCESS"` only means the operation completed (the VM ran
and returned). The command's success/failure lives in `exit_code`;
see contree://guide/errors.

## Cleanup

Untagged result images cannot be deleted explicitly through this
MCP server. They are eligible for project-scoped garbage collection
by the backend. Tag anything you want to keep; expect everything
else to eventually disappear.
"""
