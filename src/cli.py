from __future__ import annotations

import argparse
import logging
import sys
import traceback
import warnings
from pathlib import Path
from typing import Iterable, Optional

from bsutils.logger import configure_logger
from bsutils.reader import read_statement
from loguru import logger

try:
    from cryptography.utils import CryptographyDeprecationWarning
except ImportError:
    CryptographyDeprecationWarning = None

if CryptographyDeprecationWarning is not None:
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="balanceparser",
        description="BalanceParser command line interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    path_parser = subparsers.add_parser(
        "parse",
        help="Process statement PDFs in a directory.",
    )
    path_parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing statement PDFs.",
    )
    path_parser.add_argument(
        "pattern",
        nargs="?",
        default="*Statement*.pdf",
        help="Glob pattern for selecting PDFs (default: *Statement*.pdf).",
    )
    path_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging to stdout and statement.log.",
    )
    path_parser.set_defaults(func=_handle_path)

    config_parser = subparsers.add_parser(
        "config",
        help="Manage BalanceParser configuration (show, set, delete).",
    )
    config_parser.add_argument(
        "config_args",
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS,
    )
    config_parser.set_defaults(func=_handle_config)

    return parser


def _handle_path(args: argparse.Namespace) -> int:
    configure_logger(args.debug)
    directory = args.directory.expanduser().resolve()
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    process_statements(directory, args.pattern)
    return 0


def process_statements(directory: Path, pattern: str = "*.pdf") -> None:
    """Process every statement in ``directory`` that matches ``pattern``."""
    if not directory.exists() or not directory.is_dir():
        logger.error(f"Directory missing or not a folder: {directory}")
        return
    file_list = list(directory.glob(pattern))
    if not file_list:
        logger.warning(f"No files matched pattern '{pattern}' in {directory}")
        return
    for file in file_list:
        logger.info(f"Processing statement: {file}")
        try:
            read_statement(file)
        except Exception as exc:  # pragma: no cover - diagnostic path
            logger.error(f"Failed to process '{file}': {exc}\n{traceback.format_exc()}")


def _handle_config(args: argparse.Namespace) -> int:
    from config import main as config_main

    remainder = list(args.config_args or [])
    return config_main(remainder)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    if argv is None:
        raw_args = sys.argv[1:]
    else:
        raw_args = list(argv)

    command_names = {"parse", "config"}
    if not raw_args:
        raw_args = ["parse"]
    elif raw_args[0] in command_names or raw_args[0].startswith("-"):
        pass
    else:
        raw_args = ["parse", *raw_args]

    args = parser.parse_args(raw_args)
    result = args.func(args)
    return int(result) if result is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
