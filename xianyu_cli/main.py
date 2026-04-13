from __future__ import annotations

import argparse
from typing import Sequence

from xianyu_cli.commands.publish import register as register_publish


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xianyu", description="闲鱼管理系统 CLI")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    register_publish(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1

    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
