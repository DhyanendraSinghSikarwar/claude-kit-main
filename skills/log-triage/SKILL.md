---
name: log-triage
description: Use before analysing any large log dump, CI failure, crash report, or stack-trace-heavy output. Reduces raw logs to a grouped table of distinct error signatures so diagnosis works from signal rather than scrollback.
---

# Triage a log

Reduces raw log output to a small table of distinct error signatures with counts, first and
last occurrence, and one representative example each.

## Delegation

If your runtime supports subagents, spawn one with the body of `../../agents/log-triager.md`
as its instructions (ignore that file's YAML frontmatter) and pass it the log file or paste.
Tier `cheap` is sufficient — this is parsing and grouping, not reasoning. Diagnose the root
cause from its grouped table, not from the raw log.

If your runtime has no subagents, follow the procedure below inline.

## When to bother

Triage if the log is longer than about 50 lines, or mixes stack traces with routine noise.
Below that, read it directly. If the resulting table has fewer than three error groups, note
that — next time for a log of that size, reading it directly is cheaper.

## Procedure

### Step 1 — detect the format

| Looks like | Format | How to split records |
| --- | --- | --- |
| Every line starts `{` and parses as JSON | JSON lines | one object per line |
| `2024-01-01T10:00:00Z LEVEL message` | timestamped plaintext | one line per record, but see step 2 |
| `[2024-01-01 10:00:00] LEVEL [logger] msg` | bracketed plaintext | as above |
| No timestamps, freeform | unstructured | treat blank-line-separated blocks as records |

### Step 2 — reassemble multi-line records

A stack trace is **one** record, not twenty. Join a line to the record above it when the
line is indented, or begins with `at `, `File "`, `Caused by:`, `... N more`, `Traceback`,
`goroutine `, or a bare `\tat`. Getting this wrong inflates counts and destroys the grouping,
so do it before anything else.

### Step 3 — filter to signal

Drop records at `DEBUG` and `TRACE` level. Drop `INFO` unless it is the only level present.
Keep everything at `WARN`, `ERROR`, `FATAL`, `PANIC`, or `CRITICAL`.

If the log has no levels, keep records containing any of: `error`, `exception`, `failed`,
`fatal`, `panic`, `traceback`, `refused`, `timeout`, `denied` (case-insensitive).

### Step 4 — normalise into signatures

Two errors are the same problem even when their text differs in the variable parts. Before
grouping, replace these with placeholders:

| Replace | With |
| --- | --- |
| Any timestamp | `<TS>` |
| Any integer of 3+ digits | `<N>` |
| Any hex string of 6+ chars, UUID, or ULID | `<ID>` |
| Any absolute path | `<PATH>` |
| Any IP address or `host:port` | `<ADDR>` |
| Anything inside single or double quotes | `<STR>` |
| Any memory address `0x...` | `<ADDR>` |

The normalised string is the **signature**. For a stack trace, use the exception type plus
the top three frames of the trace as the signature — the deeper frames vary and the top
frames identify the site.

### Step 5 — group and count

Group records by signature. For each group record: count, first timestamp, last timestamp,
severity, and one full unmodified representative record.

### Step 6 — order by likely cause, not by count

Sort so the most diagnostic group is first. Apply these rules in order:

1. The **earliest** `FATAL` / `PANIC` / `CRITICAL` group first — a crash usually causes the
   noise after it.
2. Then any group whose first occurrence is earliest, if a cascade is visible (many distinct
   errors starting within a second or two of each other means one upstream cause).
3. Then remaining groups by count, descending.

A high count is often a symptom; the first error is more often the cause. Say explicitly
which group you believe is causal and why.

### Step 7 — output

```markdown
**Scanned**: N records, window `<first ts>` → `<last ts>`, M distinct signatures

| # | Sev | Count | First | Signature |
| --- | --- | --- | --- | --- |
| 1 | ERROR | 1 | 10:04:11 | `ConnectionRefusedError: <ADDR>` |
| 2 | ERROR | 812 | 10:04:12 | `PoolTimeout: no connection available after <N>ms` |

**Likely cause**: group 1 — it precedes group 2 by one second and group 2 is the pool
starving as a consequence.

<details><summary>Representative record, group 1</summary>

```text
<the full unmodified record>
```

</details>
```

Include a representative record for the top three groups only. Never paste the whole log
back — that defeats the purpose of triaging it.
