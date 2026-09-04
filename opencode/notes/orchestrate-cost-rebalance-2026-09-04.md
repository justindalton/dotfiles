# Orchestrate agent cost rebalance — baseline (2026-09-04)

On 2026-09-04, the `orchestrate` agent was switched from `openai/gpt-5.6-luna` to `anthropic/claude-sonnet-5`, `compaction.prune` was enabled, and `provider.anthropic.options.setCacheKey` was enabled, in dotfiles commit `b0e61ef`. This document records the trailing-30-day baseline numbers the decision was planned against, so a follow-up comparison can check whether the projected savings materialized. Note: `orchestrate` had briefly run on `openai/gpt-5.6-luna` immediately before this change, but that period is not a valid baseline for comparison — luna could not self-manage and required far more manual user direction, which is the reason for this change. The valid baseline is the prior `gpt-5.6-sol` period below.

## 30-day baseline: orchestrate on gpt-5.6-sol

Source: message-level `modelID`/`cost`/`tokens` fields (session-level `model` column is unreliable — it only records the last model used in a session, not a true breakdown).

- Total orchestrate messages: 4040
- Total billed cost: $891.00
- Cost per message: $0.2205
- Messages exceeding the 272k-token OpenAI pricing tier (2x rate): 1468 (36%)
- Cost from sub-272k messages: $445.61
- Cost from over-272k messages: $445.39 (50% of total cost from 36% of messages)

## Session-size cost concentration

| Session size (subagent dispatches) | Sessions | Cost | Share |
|---|---|---|---|
| ≤5 | 20 | $29.62 | 2.7% |
| 6–20 | 15 | $112.30 | 10.4% |
| >20 | 14 | $940.00 | 86.9% |

14 sessions (out of 49) accounted for 86.9% of orchestrate cost.

## Top cost-driving sessions (all >20 dispatches)

| Session ID (short) | Messages | Avg context | Peak context | Cost |
|---|---|---|---|---|
| fa7849c32ffe | 510 | 241K | 502K | $121.27 |
| fa5fd26b7ffe | 465 | 246K | 447K | $105.10 |
| f9801c71dffe | 316 | 322K | 517K | $102.49 |
| fb688a892ffe | 211 | 298K | 442K | $84.82 |
| fb7061ce3ffe | 308 | 278K | 461K | $71.05 |
| fa11f3063ffe | 228 | 256K | 422K | $65.16 |
| fa6394916ffe | 270 | 221K | 406K | $63.96 |
| f98b78325ffe | 217 | 269K | 396K | $51.07 |
| f97aea205ffe | 223 | 232K | 347K | $50.51 |
| fa1f69647ffe | 135 | 231K | 354K | $36.48 |

## Model comparison, modeled on the actual 4040-message orchestrate workload

Cost model applied each candidate model's published per-token rates (input/output/cache-read/cache-write) to the actual observed token counts per message, including OpenAI's 272k-context 2x pricing tier where applicable. The model reproduces the actual sol bill within ~10% ($804.25 modeled vs $891.00 actual) and is used for *relative* comparison across models, not exact re-billing.

Rates used (input / output / cache-read / cache-write per 1M tokens; "tier" = has an OpenAI-style 272k context pricing cliff):

| Model | in | out | cache-read | cache-write | 272k tier? |
|---|---|---|---|---|---|
| gpt-5.6-luna | 0.20 | 1.20 | 0.02 | 0.25 | yes |
| gpt-5.6-terra | 2.00 | 12.00 | 0.20 | 2.50 | yes |
| gpt-5.6-sol | 4.00 | 20.00 | 0.40 | 5.00 | yes |
| claude-sonnet-5 | 2.00 | 10.00 | 0.20 | 2.50 | no |
| claude-sonnet-4-6 | 3.00 | 15.00 | 0.30 | 3.75 | no |
| claude-opus-5 | 5.00 | 25.00 | 0.50 | 6.25 | no |

### As-observed context (no compaction change)

| Model | Cost | $/msg | vs sol actual | Tier-2 turns |
|---|---|---|---|---|
| gpt-5.6-luna | $40.54 | $0.0100 | 21.98x cheaper | 1468 |
| gpt-5.6-terra | $405.42 | $0.1004 | 2.20x cheaper | 1468 |
| gpt-5.6-sol (modeled) | $804.25 | $0.1991 | 1.11x (baseline) | 1468 |
| claude-sonnet-5 | $257.91 | $0.0638 | 3.45x cheaper | 0 |
| claude-sonnet-4-6 | $386.87 | $0.0958 | 2.30x cheaper | 0 |
| claude-opus-5 | $644.79 | $0.1596 | 1.38x cheaper | 0 |

### Projected with context held under 200K (prune + phase-boundary discipline)

| Model | Cost | vs sol actual |
|---|---|---|
| gpt-5.6-luna | $23.90 | 37.29x cheaper |
| gpt-5.6-terra | $238.95 | 3.73x cheaper |
| gpt-5.6-sol | $473.05 | 1.88x cheaper |
| claude-sonnet-5 | $205.47 | 4.34x cheaper |
| claude-sonnet-4-6 | $308.20 | 2.89x cheaper |
| claude-opus-5 | $513.67 | 1.73x cheaper |

## Cache-write sensitivity (Anthropic 5-minute cache TTL risk)

Sonnet-5 has no context pricing tier, but long orchestrator sessions with gaps between subagent returns could force cache TTL misses, increasing cache-write volume. Sensitivity check:

| Cache-write volume | claude-sonnet-5 | gpt-5.6-terra |
|---|---|---|
| As observed | $257.91 | $405.42 |
| 2x (TTL misses) | $322.31 | $529.38 |
| 4x (heavy churn) | $451.10 | $786.30 |
| 8x (worst case) | $708.68 | $1,292.40 |

Observed cache write:read ratio in the baseline period: 1:35.1 (write 25.8M tokens, read 904.3M tokens). Sonnet-5 wins at every level up to ~4x churn.

Sonnet-5 cost breakdown (as-observed): cache-read $181 (70%), cache-write $64 (25%), output $12 (5%). 70% of cost is re-reading already-seen context, which is what `compaction.prune` targets independent of model choice.

## Decision and projected outcome

Chosen: `anthropic/claude-sonnet-5` for `orchestrate`, plus `compaction.prune: true` and `provider.anthropic.options.setCacheKey: true` globally. Left unchanged: `review` and `architect` stay on `gpt-5.6-sol` (bounded single-shot roles, context never approaches the 272k tier); `implement`, `verify`, `explore` stay on `gpt-5.6-luna` (correct fit for scoped delegated work, $0.05–0.07/session).

**Projected orchestrate cost range: $205–258 per 30 days**, down from the $891 sol baseline (3.5x–4.3x reduction), while restoring autonomous multi-step orchestration that `gpt-5.6-luna` could not sustain.

## How to re-check next week

Re-run against the live `~/.local/share/opencode/opencode.db` SQLite database:

```sql
-- overall cost + avg context, trailing 7 days
SELECT s.agent, json_extract(m.data,'$.modelID') mdl, COUNT(*) msgs,
 ROUND(SUM(CAST(json_extract(m.data,'$.cost') AS REAL)),2) cost,
 ROUND(AVG(CAST(json_extract(m.data,'$.tokens.cache.read') AS REAL))/1000) avg_ctx_K
FROM message m JOIN session s ON s.id=m.session_id
WHERE s.agent='orchestrate' AND m.time_created > (strftime('%s','now')-7*86400)*1000
GROUP BY 1,2;
```

```sql
-- session-size concentration, trailing 7 days
WITH o AS (SELECT s.id,
  (SELECT COUNT(*) FROM session c WHERE c.parent_id=s.id) kids,
  (SELECT SUM(CAST(json_extract(m.data,'$.cost') AS REAL)) FROM message m WHERE m.session_id=s.id) cost
 FROM session s WHERE s.agent='orchestrate' AND s.time_created > (strftime('%s','now')-7*86400)*1000)
SELECT CASE WHEN kids<=5 THEN 'A: <=5 kids' WHEN kids<=20 THEN 'B: 6-20' ELSE 'C: >20' END bucket,
 COUNT(*) sessions, ROUND(SUM(cost),2) cost
FROM o GROUP BY 1 ORDER BY 1;
```

Success criteria: average context per orchestrate message (`avg_ctx_K`) should drop below ~200K, confirming `prune` is working. Weekly cost, scaled to a 30-day rate, should land in the $205–258 range. If `avg_ctx_K` stays above 250K, the session-length/wave-boundary discipline in `orchestrate.md` is being ignored and needs to become a harder constraint rather than a prose guideline.
