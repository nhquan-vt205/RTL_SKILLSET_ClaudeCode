# Session Checkpoint Template

> Internal context-recovery artifact for Claude; not a human-facing report.

## SESSION

- Session ID: `NNN`
- Timestamp: `YYYY-MM-DD HH:mm`
- Project: `<project name>`
- Status: `ONGOING | COMPLETED | BLOCKED`
- Prompt Range: `<first>-<last>`

## USER INTENT

- Goal: `<what the user wants to achieve>`
- Request: `<concise current request>`
- Constraints:
  - `<constraint>`
  - `<constraint>`

## CLAUDE ACTIONS

- `<analysis / decision / implementation performed>`
- `<important result>`
- `<important command/tool/action>`

## FILES

### Modified

- `<path>` — `<change>`

### Created

- `<path>` — `<purpose>`

### Relevant Existing Files

- `<path>` — `<why relevant>`

## TECHNICAL CONTEXT

### Current State

- `<architecture / implementation state needed to continue>`

### Important Parameters / Interfaces

- `<name>` = `<value / definition>`

### Decisions

- `DECIDED:` `<decision>`
- `DECIDED:` `<decision>`
- `SUPERSEDED:` `<old decision>` → `NEW:` `<new decision>`

## WORK STATUS

### Completed

- [x] `<completed item>`

### In Progress

- [ ] `<current work>`

### Pending / TODO

- [ ] `<next task>`

### Blockers

- `<blocker or NONE>`

## ISSUES / RISKS

- `ISSUE:` `<problem>` — `OPEN | RESOLVED | DEFERRED`
- `RISK:` `<risk>` — `<mitigation>`

## CONTEXT REFERENCES

### Previous Relevant Sessions

- `<checkpoint filename>` — `<why relevant>`

### Project References

- `<spec / RTL / doc path>` — `<why relevant>`

## NEXT CONTEXT

The next Claude instance must remember:

1. `<most important context>`
2. `<important constraint>`
3. `<what must happen next>`

### Continuation Instruction

`<one concise instruction for continuing from this checkpoint>`

## TEMPLATE RULES

- Maximum checkpoint length: 100 lines.
- Keep only information needed for context recovery.
- Do not copy the conversation verbatim.
- Do not invent missing information.
- Preserve exact file paths, module names, signal names, parameters, interfaces, addresses, and key decisions.
- Record changed decisions with `SUPERSEDED` and `NEW`.
- Prefer references to project files over duplicating their contents.
- Remove irrelevant sections instead of filling them with noise.
