"""
# Contree MCP — Quickstart

Bootstrap pattern for an agent starting a fresh task.

## 1. Pick an image

    list_images(tag_prefix="common/python")

Don't assume `tag:python:3.11` exists — pick from the actual list.

## 2. Run a one-shot command

    run(command="python -c 'print(1+1)'", image="tag:python:3.11")

Default is `disposable=true` and `shell=true`. Returns
`stdout`, `stderr`, `exit_code`.

## 3. Stage local files, then run

    rsync(source="/path/to/project", destination="/app",
          exclude=["__pycache__", "*.pyc", ".git", "node_modules"])
    # -> directory_state_id: "ds_abc123"

    run(command="python /app/main.py", image="tag:python:3.11",
        directory_state_id="ds_abc123")

Or for a single file:

    upload(path="/etc/local/config.yaml")
    # -> {"uuid": "f-1"}

    run(command="cat /etc/cfg", image="tag:python:3.11",
        files={"/etc/cfg": "f-1"})

## 4. Build a dependency chain (keep the image)

    run(command="pip install numpy pandas",
        image="tag:python:3.11", disposable=false)
    # -> result_image: "img-with-deps"

    set_tag(image_uuid="img-with-deps",
            tag="common/python-ml/python:3.11-slim")

    run(command="python /app/train.py",
        image="tag:common/python-ml/python:3.11-slim",
        directory_state_id="ds_abc123")

## 5. Import a fresh image from a registry

    import_image(registry_url="docker://docker.io/golang:1.21",
                 tag="common/golang/1.21")
    run(command="go version",
        image="tag:common/golang/1.21")

## Defaults to remember

- `disposable=true` — discards changes. Set `false` to keep state.
  (CLI users: this is the opposite of `contree run`.)
- `wait=true` — blocks. Set `false` for async; use
  `wait_operations` to join.
- `cwd=""` — image default. Set absolute path to override.
- `truncate_output_at=8000` — stdout/stderr cap. Raise to
  ~32_000 for verbose builds; for very large output, write to a
  file and `download` it.

## Env vars

Pass through `env`, not via shell `export`:

    run(command="python /app/app.py", image="tag:python:3.11",
        env={"DEBUG": "1", "API_KEY": "secret"})

For PATH-style adjustments that need to outlive the run, set
`preserve_env=true` on the `run` that establishes them:

    run(command="curl -sSf https://sh.rustup.rs | sh -s -- -y",
        image="<base>", disposable=false)
    run(command="cargo build", image="<after-rustup>",
        env={"PATH": "/root/.cargo/bin:/usr/bin:/bin"},
        preserve_env=true, disposable=false)
    # PATH is now part of the resulting image — drop preserve_env on
    # later runs that just consume it.

## See also

- contree://guide/workflow — full agent protocol
- contree://guide/state — UUID lineage, branching by re-use
- contree://guide/tagging — naming convention
"""
