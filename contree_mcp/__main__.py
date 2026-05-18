import argparse
import asyncio
import logging
import sys
from contextlib import suppress

from contree_mcp.arguments import PARSER_DESCRIPTION, PARSER_EPILOG, Parser
from contree_mcp.server import amain
from contree_mcp.update_check import UpdateChecker

log = logging.getLogger(__name__)


def main() -> None:
    parser = Parser(
        description=PARSER_DESCRIPTION,
        epilog=PARSER_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.parse_args()

    logging.basicConfig(level=parser.log_level, format="[%(levelname)s] %(message)s", stream=sys.stderr)

    # Update check runs after argparse so --help / --version skip it,
    # and so the warning respects --log-level. refresh() is best-effort;
    # is_latest() is a pure predicate.
    checker = UpdateChecker()
    with suppress(Exception):
        checker.refresh()
    if not checker.is_latest():
        log.warning(
            "A new version of contree-mcp is available: %s (installed: %s)."
            " Upgrade with `uv tool install -U contree-mcp` or"
            " `pip install -U contree-mcp`.",
            checker.state.latest_version,
            checker.current_version,
        )

    try:
        asyncio.run(amain(parser))
    except KeyboardInterrupt:
        logging.info("Gracefully exited on keyboard interrupt")


if __name__ == "__main__":
    main()
