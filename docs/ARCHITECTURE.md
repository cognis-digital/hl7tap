# HL7TAP — Architecture

> Parse, pretty-print, diff, and replay HL7 v2 messages over MLLP from the terminal.

```
input ──▶ collect ──▶ rules/analyzers ──▶ score ──▶ findings ──▶ table · json
                              │                          │
                         (this repo)                 MCP tool (agents)
```

- **collect** normalizes the target (file/dir/API) into records.
- **rules/analyzers** apply the heuristics shipped in `hl7tap/core.py`.
- **score** ranks by severity.
- **MCP server** (`hl7tap mcp`) exposes `scan` for Cognis.Studio agents.

Extend by adding a rule + a test + a `demos/NN-*/SCENARIO.md`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
