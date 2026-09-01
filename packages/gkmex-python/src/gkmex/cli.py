from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .client import DEFAULT_BASE_URL, GkmexClient, GkmexError


def _non_empty(value):
    if not value or value != value.strip():
        raise argparse.ArgumentTypeError("value must be non-empty and unpadded")
    return value


def _public_id(value):
    value = _non_empty(value)
    if value in {".", ".."}:
        raise argparse.ArgumentTypeError(
            "ID must be a canonical public crane ID"
        )
    return value


def _limit(value):
    parsed = int(value)
    if not 1 <= parsed <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return parsed


def _offset(value):
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("offset must be zero or greater")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(prog="gkmex")
    parser.add_argument(
        "--version",
        action="version",
        version=f"gkmex {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="List published cranes")
    listing.add_argument("--brand", type=_non_empty)
    listing.add_argument("--type", choices=("mobile", "crawler"))
    listing.add_argument("--limit", type=_limit)
    pagination = listing.add_mutually_exclusive_group()
    pagination.add_argument("--offset", type=_offset)
    pagination.add_argument("--cursor", type=_non_empty)

    get = commands.add_parser("get", help="Get one published crane")
    get.add_argument("id", type=_public_id)

    compare = commands.add_parser(
        "compare",
        help="Compare two to five cranes",
    )
    compare.add_argument("ids", nargs="+", type=_public_id)
    return parser


def main(argv=None):
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "compare":
        if not 2 <= len(arguments.ids) <= 5:
            parser.error("compare requires two to five public crane IDs")
        if len(set(arguments.ids)) != len(arguments.ids):
            parser.error("compare requires unique public crane IDs")

    client = GkmexClient(
        base_url=os.environ.get("GKMEX_BASE_URL", DEFAULT_BASE_URL)
    )
    try:
        if arguments.command == "list":
            result = client.list_cranes(
                brand=arguments.brand,
                type=arguments.type,
                limit=arguments.limit,
                offset=arguments.offset,
                cursor=arguments.cursor,
            )
        elif arguments.command == "get":
            result = client.get_crane(arguments.id)
        else:
            result = client.compare_cranes(arguments.ids)

        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    except GkmexError as exc:
        print(f"gkmex: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
