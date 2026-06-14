"""HL7TAP MCP server — exposes parse/diff as MCP tools for Cognis.Studio."""
from __future__ import annotations

import json
import sys

try:
    from hl7tap.core import parse_message, message_to_dict, pretty_print
    _CORE_AVAILABLE = True
except Exception as _core_err:  # pragma: no cover
    _CORE_AVAILABLE = False
    _core_err_msg = str(_core_err)


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-hl7tap[mcp]"
    """
    if not _CORE_AVAILABLE:
        print(
            f"error: hl7tap core unavailable: {_core_err_msg}",  # type: ignore[name-defined]
            file=sys.stderr,
        )
        return 1

    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-hl7tap[mcp]'")
        return 1

    app = FastMCP("hl7tap")

    @app.tool()
    def hl7tap_parse(text: str) -> str:
        """Parse an HL7 v2 message string and return a JSON representation."""
        try:
            msg = parse_message(text)
            return json.dumps(message_to_dict(msg))
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    @app.tool()
    def hl7tap_pretty(text: str) -> str:
        """Parse an HL7 v2 message string and return a human-readable table."""
        try:
            msg = parse_message(text)
            return pretty_print(msg)
        except ValueError as exc:
            return f"error: {exc}"

    app.run()
    return 0
