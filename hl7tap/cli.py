"""Command-line interface for HL7TAP - curl for HL7 v2 interfaces."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    parse_message,
    pretty_print,
    diff_messages,
    message_to_dict,
)


EXAMPLES = """\
examples:
  # Pretty-print a message
  hl7tap parse demos/01-basic/adt_a01.hl7

  # Emit structured JSON for piping into jq / CI
  hl7tap parse message.hl7 --format json | jq .message_type

  # Diff two messages (exits non-zero when they differ -- CI gate)
  hl7tap diff old.hl7 new.hl7
  hl7tap diff old.hl7 new.hl7 --format json

  # Read from stdin
  cat message.hl7 | hl7tap parse -
"""


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Parse, pretty-print, and diff HL7 v2 messages "
                    "(curl for HL7 interfaces).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")

    sub = p.add_subparsers(dest="command", metavar="<command>")

    sp = sub.add_parser("parse", help="parse and pretty-print a message")
    sp.add_argument("file", help="HL7 file path, or '-' for stdin")
    sp.add_argument("--format", choices=["table", "json"], default="table",
                    help="output format (default: table)")

    sd = sub.add_parser("diff", help="diff two HL7 messages")
    sd.add_argument("old", help="baseline HL7 file (or '-')")
    sd.add_argument("new", help="comparison HL7 file (or '-')")
    sd.add_argument("--format", choices=["table", "json"], default="table",
                    help="output format (default: table)")

    return p


def _cmd_parse(file: str, fmt: str) -> int:
    try:
        msg = parse_message(_read(file))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if fmt == "json":
        print(json.dumps(message_to_dict(msg), indent=2))
    else:
        print(pretty_print(msg))
    return 0


def _cmd_diff(old: str, new: str, fmt: str) -> int:
    try:
        a = parse_message(_read(old))
        b = parse_message(_read(new))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    diffs = diff_messages(a, b)
    if fmt == "json":
        print(json.dumps({"differences": diffs,
                          "count": len(diffs)}, indent=2))
    else:
        if not diffs:
            print("messages are identical")
        else:
            print(f"{len(diffs)} difference(s):")
            for d in diffs:
                t = d["type"]
                loc = d["location"]
                if t == "field_changed":
                    print(f"  ~ {loc}: {d['old']!r} -> {d['new']!r}")
                elif t in ("field_added", "segment_added"):
                    print(f"  + {loc}: {d.get('new')!r}")
                else:
                    print(f"  - {loc}: {d.get('old')!r}")
    # Non-zero exit when messages differ, so 'diff' works as a CI gate.
    return 1 if diffs else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "parse":
            return _cmd_parse(args.file, args.format)
        if args.command == "diff":
            return _cmd_diff(args.old, args.new, args.format)
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: unexpected failure: {exc}", file=sys.stderr)
        return 2

    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
