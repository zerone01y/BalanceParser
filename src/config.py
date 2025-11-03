from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

CONFIG_FILENAME = "BalanceParser_config.json"


Pathish = Union[str, Path]


@dataclass
class AppConfig:
    csv_dir: Path
    pdf_dir: Path

    def to_dict(self) -> dict:
        return {
            "csv_dir": str(self.csv_dir.expanduser()),
            "pdf_dir": str(self.pdf_dir.expanduser()),
        }

    @classmethod
    def from_dict(cls, data: dict, fallback: "AppConfig") -> "AppConfig":
        return cls(
            csv_dir=_coerce_path(data.get("csv_dir"), fallback.csv_dir),
            pdf_dir=_coerce_path(data.get("pdf_dir"), fallback.pdf_dir),
        )


def _coerce_path(value: Optional[Pathish], fallback: Path) -> Path:
    if value == "None":
        return None
    if not value:
        return fallback
    try:
        return Path(value).expanduser()
    except (TypeError, ValueError):
        return fallback


def get_default_config(base_dir: Optional[Path] = None) -> AppConfig:
    root = base_dir or Path.cwd()
    default_dir = root / "BankStatement"
    return AppConfig(csv_dir=default_dir, pdf_dir=default_dir)


def get_user_config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base


def get_config_path() -> Path:
    return get_user_config_dir() / CONFIG_FILENAME


def load_config() -> AppConfig:
    fallback = get_default_config()
    config_path = get_config_path()
    if not config_path.exists():
        return fallback
    try:
        data = json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback
    return AppConfig.from_dict(data, fallback)


def save_config(config: AppConfig) -> None:
    config_dir = get_user_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / CONFIG_FILENAME
    config_path.write_text(json.dumps(config.to_dict(), indent=2))


def delete_config() -> None:
    config_path = get_config_path()
    try:
        config_path.unlink()
    except FileNotFoundError:
        pass


def ensure_paths(config: AppConfig) -> AppConfig:
    csv_dir = config.csv_dir.expanduser()

    csv_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = config.pdf_dir
    if pdf_dir is not None:
        pdf_dir = pdf_dir.expanduser()
        pdf_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(csv_dir=csv_dir, pdf_dir=pdf_dir)


def update_config(
    csv_dir: Optional[Pathish] = None, pdf_dir: Optional[Pathish] = None
) -> AppConfig:
    current = load_config()
    updated = AppConfig(
        csv_dir=_coerce_path(csv_dir, current.csv_dir),
        pdf_dir=_coerce_path(pdf_dir, current.pdf_dir),
    )
    save_config(updated)
    return ensure_paths(updated)


def load_active_config() -> AppConfig:
    """Load the current configuration and ensure the target directories exist."""
    return ensure_paths(load_config())


# ----- CLI helpers -------------------------------------------------------- #


def _config_as_lines(config: AppConfig) -> str:
    return "\n".join(
        [
            f"CSV directory: {config.csv_dir}",
            f"PDF directory: {config.pdf_dir}",
        ]
    )


def _command_show(args: argparse.Namespace) -> int:
    config_path = get_config_path()
    config_exists = config_path.exists()
    config = ensure_paths(load_config())
    if config_exists:
        print(f"Config file: {config_path}")
    else:
        print("Config file: <not found — using defaults>")
    print(_config_as_lines(config))
    return 0


def _command_set(args: argparse.Namespace) -> int:
    if args.csv is None and args.pdf is None:
        raise SystemExit("Nothing to update: provide --csv and/or --pdf.")
    config = update_config(csv_dir=args.csv, pdf_dir=args.pdf)
    print(f"Updated configuration at {get_config_path()}")
    print(_config_as_lines(config))
    return 0


def _command_delete(args: argparse.Namespace) -> int:
    config_path = get_config_path()
    if not config_path.exists():
        print("No configuration file to delete.")
        return 0
    delete_config()
    print(f"Deleted configuration file at {config_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage BalanceParser configuration.")
    subparsers = parser.add_subparsers(dest="command")

    show_parser = subparsers.add_parser(
        "show", help="Display the active configuration."
    )
    show_parser.set_defaults(func=_command_show)

    set_parser = subparsers.add_parser(
        "set", help="Update directories for CSV/PDF outputs."
    )
    set_parser.add_argument("--csv", type=str, help="Directory for exported CSV files.")
    set_parser.add_argument("--pdf", type=str, help="Directory for archived PDFs.")
    set_parser.set_defaults(func=_command_set)

    delete_parser = subparsers.add_parser(
        "delete", help="Remove the stored configuration file."
    )
    delete_parser.set_defaults(func=_command_delete)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
