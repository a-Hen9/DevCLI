"""DevCLI main entry point."""
import asyncio
import sys
from pathlib import Path

from devcli.app import DevCLIApp


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="DevCLI - AI Full-Stack Development Agent")
    parser.add_argument("--project-dir", default=str(Path.cwd()), help="Project directory")
    parser.add_argument("--requirement", default="", help="Initial requirement")
    args = parser.parse_args()

    app = DevCLIApp(
        project_dir=args.project_dir,
        requirement=args.requirement,
    )
    app.run()


if __name__ == "__main__":
    main()
