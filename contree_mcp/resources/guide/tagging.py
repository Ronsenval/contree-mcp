"""
# Contree MCP — Tag Convention

Tags make images discoverable by future runs and other agents.
Without tags, useful images can only be reached by UUID and easily
drop out of working memory.

Tags are unique per project: assigning a tag to a UUID moves it
away from whatever image previously held it.

## Format

    {scope}/{purpose}/{base}:{tag}

| Field | Meaning | Examples |
|-------|---------|----------|
| `scope` | `common` or `<project>` | `common`, `myproject` |
| `purpose` | What was added | `rust-toolchain`, `python-ml`, `web-deps` |
| `base:tag` | Origin image | `ubuntu:noble`, `python:3.11-slim` |

Canonical examples:

    common/rust-toolchain/ubuntu:noble       # ubuntu + rustup
    common/python-ml/python:3.11-slim        # numpy + pandas + sklearn
    common/python-web/python:3.11-slim       # flask / fastapi
    common/node/alpine:20                    # node 20 on alpine
    common/build-essentials/alpine:latest    # gcc, make, cmake
    myproject/dev-env/python:3.11-slim       # project-specific

## When to tag as `common/` vs `<project>/`

`common/` — generic tooling that other tasks can reuse:
  - Standard packages (build-essential, curl, git).
  - Language runtimes / compilers (rust, go, node).
  - Widely-used libraries (numpy, pandas, flask).

`<project>/` — anything carrying application code, secrets, or
a project-specific configuration. Don't pollute `common/` with
project state.

## Tag rules

- Allowed characters: `a-z 0-9 _ -`, with `: / .` as separators
  (max 256 chars).
- Your project's tags shadow public tags of the same name.
  Removing your tag restores the public one.
- Removing a tag from an image in the public namespace yields a
  reassigned tag in the response (the tag follows the public
  image), not a deletion.

## Always search before building

    list_images(tag_prefix="common/python")

Common prefixes worth probing:

| Prefix | Likely contents |
|--------|-----------------|
| `common/python-ml` | numpy, pandas, scikit-learn |
| `common/python-web` | flask, fastapi, requests |
| `common/rust-toolchain` | rustc, cargo |
| `common/node` | node, npm, common packages |
| `common/build-essentials` | gcc, make, cmake |

Importing a ready-made image (`import_image`) is almost always
cheaper than re-installing from scratch.

## Tag right after the non-disposable run

    run(command="pip install numpy pandas scikit-learn",
        image="tag:python:3.11-slim", disposable=false)
    # -> result_image "uuid-with-deps"

    set_tag(image_uuid="uuid-with-deps",
            tag="common/python-ml/python:3.11-slim")

Subsequent agents land on the tagged image without rebuilding.

## Untagging

    set_tag(image_uuid="<uuid>", tag="")     # remove all tags
    # -> Image with tag=null

The image keeps its UUID and stays reachable; only the tag goes.
"""
