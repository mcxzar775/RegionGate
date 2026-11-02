import argparse
import logging
import os

from regiongate_agent.config import get_settings
from regiongate_agent.server import serve_forever


def main() -> None:
    parser = argparse.ArgumentParser(description="RegionGate Gateway Agent")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode")
    parser.add_argument("--socket", default=None, help="Unix socket path")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["REGIONGATE_AGENT_DRY_RUN"] = "1"
    if args.socket:
        os.environ["REGIONGATE_AGENT_SOCKET_PATH"] = args.socket

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    logging.info("starting agent dry_run=%s socket=%s", settings.dry_run, settings.socket_path)
    serve_forever()


if __name__ == "__main__":
    main()
