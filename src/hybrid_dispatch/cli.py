"""Command-line interface."""

from __future__ import annotations

import argparse
import json

from hybrid_dispatch.config import ProjectConfig, load_config
from hybrid_dispatch.reporting import run_reference


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Hybrid renewable-energy feasibility optimiser")
    commands = root.add_subparsers(dest="command", required=True)
    reproduce = commands.add_parser("reproduce", help="Regenerate the reference case")
    reproduce.add_argument("--output", default="results/reference")
    reproduce.add_argument("--config", default=None, help="Optional JSON assumptions file")
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "reproduce":
        config = load_config(arguments.config) if arguments.config else ProjectConfig()
        result = run_reference(output_dir=arguments.output, config=config)
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
