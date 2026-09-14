# Architect escalation re-check (2026-09-14)

## Baseline and observations

In the prior 14 days, telemetry recorded 141 `architect` calls across 25
sessions, or 5.6 calls per architect-using session. Calls spiked after the
September 8 routing rewrite. A sample of briefs was mostly routine. These are
observed timing and sampling results, not proof that the rewrite caused the
spike or that routine briefs caused every call.

## Root causes and decisions

The seven prompt conditions selected for correction were: architect remaining
a normal routing-table lane; an ambiguous material-risk qualifier; no
same-model/default/cost framing; an early failure escape hatch; user intent
routed to architect despite the question tool; a plural batching cue; and an
unconditional final-report cue. The approved prompt-only reduction makes
orchestrate the session architect, requires the three conjunctive risk/options
gates (or the separate two-failure path), routes unresolved product intent to
the question tool, rejects routine briefs without analysis, and caps
consultation at one per session. These are prompt observations and correction
decisions, not proof of causality beyond the observed timing and sampling.

## Exact re-check SQL

Run against `~/.local/share/opencode/opencode.db` for the trailing 7 days. Task
dispatches are `part` records identified by the nested `subagent_type` field.

```sql
WITH task_calls AS (
  SELECT
    date(time_created / 1000, 'unixepoch') AS day,
    json_extract(data, '$.state.input.subagent_type') AS subagent_type
  FROM part
  WHERE time_created > (strftime('%s', 'now') - 7 * 86400) * 1000
    AND json_extract(data, '$.state.input.subagent_type') IN ('architect', 'implement')
)
SELECT
  day,
  SUM(subagent_type = 'architect') AS architect_calls,
  SUM(subagent_type = 'implement') AS implement_calls,
  ROUND(100.0 * SUM(subagent_type = 'architect') /
    NULLIF(SUM(subagent_type = 'implement'), 0), 2) AS architect_pct_of_implement_calls
FROM task_calls
GROUP BY day
ORDER BY day;
```

Compact aggregate for the same trailing 7-day window:

```sql
WITH task_calls AS (
  SELECT session_id,
    json_extract(data, '$.state.input.subagent_type') AS subagent_type
  FROM part
  WHERE time_created > (strftime('%s', 'now') - 7 * 86400) * 1000
    AND json_extract(data, '$.state.input.subagent_type') IN ('architect', 'implement')
), per_session AS (
  SELECT session_id,
    SUM(subagent_type = 'architect') AS architect_calls,
    SUM(subagent_type = 'implement') AS implement_calls
  FROM task_calls
  GROUP BY session_id
)
SELECT
  SUM(architect_calls) AS architect_calls,
  SUM(architect_calls > 0) AS sessions_with_architect,
  ROUND(1.0 * SUM(architect_calls) /
    NULLIF(SUM(architect_calls > 0), 0), 2) AS calls_per_architect_session,
  SUM(implement_calls) AS implement_calls,
  ROUND(100.0 * SUM(architect_calls) /
    NULLIF(SUM(implement_calls), 0), 2) AS architect_pct_of_implement_calls,
  MAX(architect_calls) AS max_architect_calls_in_one_session
FROM per_session;
```

Also sample the corresponding architect briefs and classify them against the
three bars; success means architect is at most 2% of implement dispatches, at
most one consultation per session, and sampled briefs are legitimate
risk-class escalations.

If prompt-only enforcement remains ineffective, fall back to asking
`task.architect` explicitly at the dispatch boundary by setting
`orchestrate` permission `task.architect: ask` (do not make that permission
change as part of this note).
