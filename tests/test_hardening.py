"""Hardening tests: error paths, edge cases, and input validation."""
from __future__ import annotations

import importlib
import json
import os

import pytest

from hl7tap.cli import main
from hl7tap.core import (
    diff_messages,
    message_to_dict,
    parse_message,
    parse_segment,
    pretty_print,
)

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "demos", "01-basic")
DEMO = os.path.join(DEMO_DIR, "adt_a01.hl7")


# ---------------------------------------------------------------------------
# core.py — input validation edge cases
# ---------------------------------------------------------------------------


def test_parse_message_none_like_input():
    """All-whitespace input should raise ValueError, not AttributeError."""
    with pytest.raises(ValueError, match="empty"):
        parse_message("   \n\t  ")


def test_parse_message_no_msh_raises():
    with pytest.raises(ValueError, match="MSH"):
        parse_message("EVN|A01|20240101\r")


def test_parse_message_msh_too_short():
    """MSH with no field-separator byte should raise ValueError."""
    with pytest.raises(ValueError):
        parse_message("MSH")


def test_parse_segment_name_only():
    """A segment line with only the 3-char name and no fields is valid."""
    seg = parse_segment("ZZZ")
    assert seg.name == "ZZZ"
    assert seg.fields == []


def test_parse_segment_too_short():
    with pytest.raises(ValueError, match="too short"):
        parse_segment("AB")


def test_segment_field_out_of_range_returns_none():
    """field() beyond the end must return None, not raise."""
    seg = parse_segment("PID|1||foo")
    assert seg.field(999) is None
    assert seg.field(0) is None


def test_message_no_msh_properties_are_empty():
    """message_type / control_id on a message with no MSH must return ''."""
    from hl7tap.core import Delimiters, Message, Segment, Field, Component
    msg = Message(
        segments=[Segment("EVN", [Field([[Component(["A01"])]])])],
        delimiters=Delimiters(),
    )
    assert msg.message_type == ""
    assert msg.control_id == ""


def test_diff_messages_added_and_removed_segments():
    """diff_messages handles segment_added and segment_removed records."""
    a = parse_message(
        "MSH|^~\\&|A|B|||20230101||ADT^A01|1|P|2.5\r"
        "PID|1|||Doe^John"
    )
    b = parse_message(
        "MSH|^~\\&|A|B|||20230101||ADT^A01|1|P|2.5\r"
        "OBX|1||result"
    )
    diffs = diff_messages(a, b)
    types = {d["type"] for d in diffs}
    assert "segment_removed" in types
    assert "segment_added" in types


def test_diff_messages_empty_vs_populated():
    """Diffing a minimal message against a fuller one never raises."""
    a = parse_message("MSH|^~\\&|A|B|||20230101||ADT^A01|1|P|2.5")
    b = parse_message(
        "MSH|^~\\&|A|B|||20230101||ADT^A01|2|P|2.5\r"
        "PID|1|||Doe^John"
    )
    diffs = diff_messages(a, b)
    assert isinstance(diffs, list)
    assert len(diffs) >= 1


def test_pretty_print_empty_fields_skipped():
    """pretty_print on a minimal message should not crash and returns a string."""
    msg = parse_message("MSH|^~\\&|A|B|||20230101||ADT^A01|1|P|2.5")
    out = pretty_print(msg)
    assert "Message-Type" in out


def test_message_to_dict_is_json_serialisable_with_minimal_message():
    msg = parse_message("MSH|^~\\&|A|B|||20230101||ADT^A01|1|P|2.5")
    d = message_to_dict(msg)
    serialised = json.dumps(d)
    back = json.loads(serialised)
    assert back["message_type"] == "ADT^A01"


# ---------------------------------------------------------------------------
# cli.py — error paths
# ---------------------------------------------------------------------------


def test_cli_parse_missing_file_exits_2(capsys):
    rc = main(["parse", "/no/such/file_xyz_12345.hl7"])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


def test_cli_diff_missing_file_exits_2(capsys):
    rc = main(["diff", "/no/such/a.hl7", "/no/such/b.hl7"])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


def test_cli_parse_malformed_content_exits_2(capsys, tmp_path):
    bad = tmp_path / "bad.hl7"
    bad.write_text("NOT_HL7_AT_ALL\n", encoding="utf-8")
    rc = main(["parse", str(bad)])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


def test_cli_parse_empty_file_exits_2(capsys, tmp_path):
    empty = tmp_path / "empty.hl7"
    empty.write_text("", encoding="utf-8")
    rc = main(["parse", str(empty)])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


def test_cli_no_subcommand_exits_nonzero(capsys):
    """Invoking hl7tap with no subcommand should return a non-zero exit code."""
    rc = main([])
    assert rc != 0


def test_cli_parse_json_missing_file_exits_2(capsys):
    rc = main(["parse", "/nonexistent.hl7", "--format", "json"])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# mcp_server.py — importable without crashing
# ---------------------------------------------------------------------------


def test_mcp_server_importable():
    """mcp_server must import cleanly (no longer crashes on missing scan/to_json)."""
    import hl7tap.mcp_server as mod
    importlib.reload(mod)
    assert hasattr(mod, "serve")
    assert callable(mod.serve)


def test_mcp_server_serve_returns_nonzero_without_mcp(monkeypatch):
    """serve() returns 1 when the 'mcp' package is not installed."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "mcp.server.fastmcp":
            raise ImportError("mcp not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    import hl7tap.mcp_server as mod
    assert mod.serve() == 1
