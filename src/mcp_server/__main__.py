import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Claude Desktop does not start in the project folder, so the .env is found by path, not by working directory.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.mcp_server.server import create_server  # noqa: E402


def main() -> None:
    # stdout belongs to the MCP protocol: logs go to stderr, and the start-up banner is off.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    create_server().run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
