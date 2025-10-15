# Demo 01 - Basic parse and diff

This demo shows HL7TAP parsing and diffing real HL7 v2 ADT messages.

## Files

- `adt_a01.hl7` - an ADT^A01 (patient admit) message.
- `adt_a01_changed.hl7` - the same message with the patient's address
  and attending physician changed.

## What it shows

### Parse / pretty-print

```
python -m hl7tap parse demos/01-basic/adt_a01.hl7
```

Expected: a human-readable, indented breakdown of every segment and
field. The header summary reports:

- `Message-Type : ADT^A01`
- `Control-ID   : MSG00001`
- the auto-detected delimiters (`field='|'  comp='^'  rep='~'  sub='&'`)

The `PID-5` patient name field decomposes into components
(`Doe` / `John` / `A`), and `PID-3` shows the patient identifier list.

### JSON output (for piping / CI)

```
python -m hl7tap parse demos/01-basic/adt_a01.hl7 --format json
```

Expected: a JSON object with `message_type`, `control_id`, detected
`delimiters`, and the full `segments` list. `message_type` is `ADT^A01`.

### Diff (CI gate)

```
python -m hl7tap diff demos/01-basic/adt_a01.hl7 demos/01-basic/adt_a01_changed.hl7
```

Expected: HL7TAP reports the changed fields:

- `PID-11` (patient address) changed
- `PV1-7` (attending physician) changed

The command exits with status **1** because the messages differ, so it
can be used as a regression gate in CI. Diffing a file against itself
exits **0** and prints `messages are identical`.
