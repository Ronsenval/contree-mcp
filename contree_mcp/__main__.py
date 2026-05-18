import asyncio
import logging
import sys

from contree_mcp.arguments import Parser
from contree_mcp.server import amain


def main() -> None:
    parser = Parser()
    parser.parse_args()

    logging.basicConfig(level=parser.log_level, format="[%(levelname)s] %(message)s", stream=sys.stderr)
    try:
        asyncio.run(amain(parser))
    except KeyboardInterrupt:
        logging.info("Gracefully exited on keyboard interrupt")


if __name__ == "__main__":
    main()
