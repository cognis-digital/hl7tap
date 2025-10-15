"""HL7TAP MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from hl7tap.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-hl7tap[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-hl7tap[mcp]'")
        return 1
    app = FastMCP("hl7tap")

    @app.tool()
    def hl7tap_scan(target: str) -> str:
        """Parse, pretty-print, diff, and replay HL7 v2 messages over MLLP from the terminal.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
