"""HL7 v2 parsing engine - standard library only.

HL7 v2 messages are pipe-delimited. A message is a sequence of segments
(one per line). Each segment starts with a 3-char name (MSH, PID, ...)
followed by fields separated by ``|``. Fields may contain repetitions
(``~``), components (``^``), and sub-components (``&``). ``\\`` is the
escape character.

The MSH segment is special: MSH-1 is the field separator itself and
MSH-2 is the encoding-characters string, so field numbering for MSH is
shifted by one relative to other segments.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import List, Optional


@dataclass(frozen=True)
class Delimiters:
    field: str = "|"
    component: str = "^"
    repetition: str = "~"
    escape: str = "\\"
    subcomponent: str = "&"


DEFAULT_DELIMITERS = Delimiters()


@dataclass
class Component:
    """A component value, optionally split into sub-components."""
    subcomponents: List[str]

    @property
    def value(self) -> str:
        return self.subcomponents[0] if self.subcomponents else ""

    def text(self, delim: Delimiters) -> str:
        return delim.subcomponent.join(self.subcomponents)


@dataclass
class Field:
    """A field, which is a list of repetitions; each repetition is a list
    of components."""
    repetitions: List[List[Component]] = dc_field(default_factory=list)

    @property
    def value(self) -> str:
        if not self.repetitions or not self.repetitions[0]:
            return ""
        return self.repetitions[0][0].value

    def text(self, delim: Delimiters) -> str:
        reps = []
        for rep in self.repetitions:
            reps.append(delim.component.join(c.text(delim) for c in rep))
        return delim.repetition.join(reps)


@dataclass
class Segment:
    name: str
    fields: List[Field]  # does NOT include the segment name
    raw: str = ""

    def field(self, index: int) -> Optional[Field]:
        """Return field by 1-based HL7 index (e.g. PID-3).

        For MSH, index 1 is the field separator and index 2 the encoding
        characters; these are synthesized so callers can use natural HL7
        numbering for every segment type.
        """
        i = index - 1
        if 0 <= i < len(self.fields):
            return self.fields[i]
        return None


@dataclass
class Message:
    segments: List[Segment]
    delimiters: Delimiters
    raw: str = ""

    def segment(self, name: str) -> Optional[Segment]:
        for s in self.segments:
            if s.name == name:
                return s
        return None

    @property
    def message_type(self) -> str:
        msh = self.segment("MSH")
        if not msh:
            return ""
        f = msh.field(9)
        return f.text(self.delimiters) if f else ""

    @property
    def control_id(self) -> str:
        msh = self.segment("MSH")
        if not msh:
            return ""
        f = msh.field(10)
        return f.value if f else ""


def _split_keep(value: str, sep: str) -> List[str]:
    return value.split(sep) if value != "" else [""]


def _parse_field_value(value: str, delim: Delimiters) -> Field:
    repetitions: List[List[Component]] = []
    for rep in _split_keep(value, delim.repetition):
        components: List[Component] = []
        for comp in _split_keep(rep, delim.component):
            subs = _split_keep(comp, delim.subcomponent)
            components.append(Component(subs))
        repetitions.append(components)
    return Field(repetitions)


def parse_segment(line: str, delim: Delimiters = DEFAULT_DELIMITERS) -> Segment:
    """Parse a single segment line into a :class:`Segment`."""
    line = line.rstrip("\r")
    if len(line) < 3:
        raise ValueError(f"segment too short to have a name: {line!r}")
    name = line[:3]
    if name == "MSH":
        # MSH-1 = field separator char, MSH-2 = encoding chars.
        if len(line) < 4:
            raise ValueError("MSH segment missing field separator")
        field_sep = line[3]
        rest = line[4:]
        raw_fields = rest.split(field_sep)
        # raw_fields[0] is the encoding-characters string (MSH-2).
        fields = [
            Field([[Component([field_sep])]]),  # MSH-1
            Field([[Component([raw_fields[0]])]]),  # MSH-2 (literal)
        ]
        for rf in raw_fields[1:]:
            fields.append(_parse_field_value(rf, delim))
        return Segment(name=name, fields=fields, raw=line)

    raw_fields = line.split(delim.field)[1:]
    fields = [_parse_field_value(rf, delim) for rf in raw_fields]
    return Segment(name=name, fields=fields, raw=line)


def _detect_delimiters(text: str) -> Delimiters:
    """Read the MSH header to discover the encoding characters."""
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        if line.startswith("MSH") and len(line) >= 8:
            field_sep = line[3]
            enc = line[4:].split(field_sep)[0]
            comp = enc[0] if len(enc) > 0 else "^"
            rep = enc[1] if len(enc) > 1 else "~"
            esc = enc[2] if len(enc) > 2 else "\\"
            sub = enc[3] if len(enc) > 3 else "&"
            return Delimiters(field_sep, comp, rep, esc, sub)
    return DEFAULT_DELIMITERS


def parse_message(text: str) -> Message:
    """Parse a full HL7 v2 message string into a :class:`Message`.

    Accepts ``\\r``, ``\\n`` or ``\\r\\n`` segment terminators. Raises
    :class:`ValueError` when no MSH header is present.
    """
    if not text or not text.strip():
        raise ValueError("empty message")
    delim = _detect_delimiters(text)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in normalized.split("\n") if ln.strip()]
    if not lines:
        raise ValueError("no segments found")
    segments = [parse_segment(ln, delim) for ln in lines]
    if segments[0].name != "MSH":
        raise ValueError(
            f"HL7 message must begin with MSH, found {segments[0].name!r}"
        )
    return Message(segments=segments, delimiters=delim, raw=text)


def message_to_dict(msg: Message) -> dict:
    """Serialize a message to a JSON-friendly dict."""
    d = msg.delimiters
    out = {
        "delimiters": {
            "field": d.field,
            "component": d.component,
            "repetition": d.repetition,
            "escape": d.escape,
            "subcomponent": d.subcomponent,
        },
        "message_type": msg.message_type,
        "control_id": msg.control_id,
        "segments": [],
    }
    for seg in msg.segments:
        fields = []
        for fld in seg.fields:
            fields.append(fld.text(d))
        out["segments"].append({"name": seg.name, "fields": fields})
    return out


def pretty_print(msg: Message) -> str:
    """Render a human-readable, indented view of a message."""
    d = msg.delimiters
    lines: List[str] = []
    lines.append(f"Message-Type : {msg.message_type or '(none)'}")
    lines.append(f"Control-ID   : {msg.control_id or '(none)'}")
    lines.append(
        "Delimiters   : field={!r} comp={!r} rep={!r} sub={!r}".format(
            d.field, d.component, d.repetition, d.subcomponent
        )
    )
    lines.append("")
    for seg in msg.segments:
        lines.append(seg.name)
        for fi, fld in enumerate(seg.fields, start=1):
            label = f"{seg.name}-{fi}"
            if len(fld.repetitions) == 1 and len(fld.repetitions[0]) == 1:
                val = fld.repetitions[0][0].text(d)
                if val == "":
                    continue
                lines.append(f"  {label:<10} {val}")
            else:
                lines.append(f"  {label}")
                for ri, rep in enumerate(fld.repetitions, start=1):
                    for ci, comp in enumerate(rep, start=1):
                        val = comp.text(d)
                        if val == "":
                            continue
                        rep_tag = f"[{ri}]" if len(fld.repetitions) > 1 else ""
                        lines.append(
                            f"    {label}.{ci}{rep_tag:<4} {val}"
                        )
    return "\n".join(lines)


def diff_messages(a: Message, b: Message) -> List[dict]:
    """Field-level diff between two messages.

    Walks segments positionally (by occurrence index of each segment name)
    and reports added/removed segments and changed/added/removed fields.
    Returns a list of difference records. An empty list means identical.
    """
    da, db = a.delimiters, b.delimiters
    diffs: List[dict] = []

    def index_segments(msg: Message):
        counts: dict = {}
        indexed: dict = {}
        for seg in msg.segments:
            n = counts.get(seg.name, 0)
            indexed[(seg.name, n)] = seg
            counts[seg.name] = n + 1
        return indexed

    ia, ib = index_segments(a), index_segments(b)
    keys = list(ia.keys())
    for k in ib.keys():
        if k not in ia:
            keys.append(k)

    for key in keys:
        name, occ = key
        seg_a = ia.get(key)
        seg_b = ib.get(key)
        loc = f"{name}[{occ}]" if (seg_a and name in [s.name for s in a.segments] and
                                   [s.name for s in a.segments].count(name) > 1) else name
        if occ > 0:
            loc = f"{name}#{occ + 1}"
        if seg_a is None:
            diffs.append({"type": "segment_added", "location": loc,
                          "new": seg_b.raw if seg_b else ""})
            continue
        if seg_b is None:
            diffs.append({"type": "segment_removed", "location": loc,
                          "old": seg_a.raw})
            continue
        n = max(len(seg_a.fields), len(seg_b.fields))
        for fi in range(n):
            fa = seg_a.fields[fi].text(da) if fi < len(seg_a.fields) else None
            fb = seg_b.fields[fi].text(db) if fi < len(seg_b.fields) else None
            field_loc = f"{loc}-{fi + 1}"
            if fa == fb:
                continue
            if fa is None:
                diffs.append({"type": "field_added", "location": field_loc,
                              "new": fb})
            elif fb is None:
                diffs.append({"type": "field_removed", "location": field_loc,
                              "old": fa})
            else:
                diffs.append({"type": "field_changed", "location": field_loc,
                              "old": fa, "new": fb})
    return diffs
