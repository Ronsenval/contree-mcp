"""Agent-facing guide sections, one module per section.

Each ``contree_mcp.resources.guide.<section>`` module is a near-empty file
whose module docstring *is* the rendered guide text. Keeping the prose in
``__doc__`` means it stays inside Python (so callers can ``from ... import
SECTIONS``), survives `dedent` for free, and is editable as plain text
without quoting / escaping concerns.

The voice / structure mirrors ``contree-cli``'s ``contree agent`` and skill
body — numbered agent protocol, "Non-negotiable rules" callouts, ``Wrong ``
/ ``Right `` examples, CLI-like topic naming. Two material differences from
the CLI are documented inline in the sections themselves:

* The MCP server is stateless: no ``-S <key>`` sessions and no
  ``session branch / checkout / rollback``. Lineage flows through
  ``result_image`` UUIDs returned by ``run`` (with ``disposable=false``)
  and ``set_tag``.
* ``disposable`` defaults to ``True`` on the MCP ``run`` tool; ``contree
  run`` defaults to non-disposable. Agents migrating from the CLI must
  opt in with ``disposable=false`` to keep state.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from textwrap import dedent
from types import MappingProxyType

# Section key -> module name. ``async`` is a Python keyword, so the module
# is spelled out fully (``asynchronous.py``) and remapped here.
_MODULES: Mapping[str, str] = MappingProxyType(
    {
        "workflow": "workflow",
        "reference": "reference",
        "quickstart": "quickstart",
        "state": "state",
        "async": "asynchronous",
        "tagging": "tagging",
        "errors": "errors",
    },
)


def _load(module_name: str) -> str:
    module = importlib.import_module(f"{__name__}.{module_name}")
    return dedent(module.__doc__ or "").strip()


SECTIONS: Mapping[str, str] = MappingProxyType(
    {section: _load(module_name) for section, module_name in _MODULES.items()},
)

__all__ = ["SECTIONS"]
