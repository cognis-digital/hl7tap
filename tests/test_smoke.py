"""Smoke tests for HL7TAP - import the core engine, run on the demo files."""
import json
import os
import subprocess
import sys

import pytest

from hl7tap import (
    TOOL_NAME,
    TOOL_VERSION,
    parse_message,
    pretty_print,
    diff_messages,
    message_to_dict,
)
from hl7tap.cli import main

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "demos", "01-basic")
DEMO = os.path.join(DEMO_DIR, "adt_a01.hl7")
DEMO_CHANGED = os.path.join(DEMO_DIR, "adt_a01_changed.hl7")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_metadata():
    assert TOOL_NAME == "hl7tap"
    assert TOOL_VERSION.count(".") == 2


def test_parse_demo_structure():
    msg = parse_message(_read(DEMO))
    assert msg.message_type == "ADT^A01"
    assert msg.control_id == "MSG00001"
    assert [s.name for s in msg.segments] == ["MSH", "EVN", "PID", "PV1"]
    # auto-detected delimiters from the MSH header
    assert msg.delimiters.field == "|"
    assert msg.delimiters.component == "^"
    assert msg.delimiters.subcomponent == "&"


def test_msh_field_numbering():
    msg = parse_message(_read(DEMO))
    msh = msg.segment("MSH")
    # MSH-1 is the field separator, MSH-2 the encoding chars.
    assert msh.field(1).value == "|"
    assert msh.field(2).value == "^~\\&"
    assert msh.field(9).text(msg.delimiters) == "ADT^A01"
    assert msh.field(10).value == "MSG00001"


def test_components_and_repetitions():
    msg = parse_message(_read(DEMO))
    pid = msg.segment("PID")
    # PID-5 patient name decomposes into components.
    name = pid.field(5)
    comps = name.repetitions[0]
    assert [c.value for c in comps] == ["Doe", "John", "A"]
    # PID-3 has two repetitions (~).
    pid3 = pid.field(3)
    assert len(pid3.repetitions) == 2


def test_pretty_print_contains_summary():
    msg = parse_message(_read(DEMO))
    out = pretty_print(msg)
    assert "Message-Type : ADT^A01" in out
    assert "PID" in out
    assert "Doe" in out


def test_message_to_dict_roundtrip_json():
    msg = parse_message(_read(DEMO))
    d = message_to_dict(msg)
    s = json.dumps(d)  # must be JSON-serializable
    back = json.loads(s)
    assert back["message_type"] == "ADT^A01"
    assert back["segments"][0]["name"] == "MSH"


def test_diff_identical_is_empty():
    msg = parse_message(_read(DEMO))
    assert diff_messages(msg, msg) == []


def test_diff_detects_changes():
    a = parse_message(_read(DEMO))
    b = parse_message(_read(DEMO_CHANGED))
    diffs = diff_messages(a, b)
    locations = {d["location"] for d in diffs}
    assert "PID-11" in locations
    assert "PV1-7" in locations
    for d in diffs:
        assert d["type"] == "field_changed"


def test_parse_rejects_non_msh():
    with pytest.raises(ValueError):
        parse_message("PID|1||foo")


def test_parse_rejects_empty():
    with pytest.raises(ValueError):
        parse_message("   ")


def test_cli_parse_table_exit_zero(capsys):
    rc = main(["parse", DEMO])
    assert rc == 0
    assert "ADT^A01" in capsys.readouterr().out


def test_cli_parse_json(capsys):
    rc = main(["parse", DEMO, "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["control_id"] == "MSG00001"


def test_cli_diff_exit_nonzero_when_different(capsys):
    rc = main(["diff", DEMO, DEMO_CHANGED])
    assert rc == 1
    assert "difference" in capsys.readouterr().out


def test_cli_diff_exit_zero_when_same():
    rc = main(["diff", DEMO, DEMO])
    assert rc == 0


def test_cli_diff_json_count(capsys):
    rc = main(["diff", DEMO, DEMO_CHANGED, "--format", "json"])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == len(data["differences"]) >= 2


def test_module_entrypoint_runs():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc = subprocess.run(
        [sys.executable, "-m", "hl7tap", "--version"],
        cwd=repo_root, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "hl7tap" in proc.stdout
