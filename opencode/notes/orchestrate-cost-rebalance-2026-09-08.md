# Orchestrate agent cost rebalance — follow-up (2026-09-08)

This is a follow-up to the 2026-09-04 change documented in [orchestrate-cost-rebalance-2026-09-04.md](orchestrate-cost-rebalance-2026-09-04.md).

## Observed regression

Live `~/.local/share/opencode/opencode.db` telemetry over the trailing 7-day window ending 2026-09-08 showed a regression under `claude-sonnet-5`:

- The bash:task dispatch ratio rose from 0.92–1.20 for the sol baseline (Aug 31–Sep 3) to 3.19–4.60 for sonnet-5 (Sep 4 and Sep 8).
- Average assistant output tokens per message rose from 151–222 to 541–560.
- Average context per message was 158–180K, down from sol's 209–249K, confirming that `compaction.prune` worked.

Root causes identified:

1. Sonnet defaults to bash over subagents.
2. `bash: {"*": "deny"}` blocked all dev-stack/process visibility (pm2, curl health checks, herdr, lsof) that the `mutiny-frontend-run-and-operate` skill instructs it to use, causing fallback to the unrestricted `general` subagent (16 dispatches versus implement's 6 on Sep 8).
3. `textVerbosity: low` is an OpenAI-specific knob with no effect on Anthropic models.

## Decision

Switch `orchestrate` to `openai/gpt-5.6-terra` ($2/$12 per 1M input/output tokens, versus sol's $4/$20 and luna's $0.20/$1.20). This restores the OpenAI-family prompt-adherence behavior (delegation-first, low output) while staying well under sol's cost.

## Cliff guardrail

The exact mechanism in `packages/opencode/src/session/overflow.ts` is: for OpenAI models with `limit.input` set (terra: 922,000), `usable = limit.input - compaction.reserved`, and auto-compaction triggers when `tokens.total >= usable`. The default `reserved` is `min(20000, maxOutputTokens)`, meaning compaction was structurally unreachable until approximately 902K context. That is why the sol baseline hit the 272K pricing cliff on 36% of messages.

Setting `compaction.reserved: 662000` forces `usable = 260,000`, keeping every OpenAI-family agent (`orchestrate`, `architect`, `review`, `implement`, `verify`, `explore`) under the 272K cliff. Anthropic models have no `limit.input`, so they use a different branch (`context - maxOutputTokens`) and are unaffected by this setting. This is safe for `plan` (`opus-5`/`sonnet-5`) and any other Anthropic agents.

## Delegation and prompt changes

A new `operate` subagent (`openai/gpt-5.6-luna`) gives `orchestrate` cheap, delegated dev-stack/process/health visibility without expanding `orchestrate`'s own bash surface, closing the `general`-fallback gap.

The new `orchestrate.md` prompt structure adds a routing table, workdir-not-`cd` rule, output budget (10/20 lines), and git-probe de-duplication rule to curb the observed bash-over-subagent and verbosity behavior.

Playwright MCP tool permissions on `orchestrate` were left unrestricted by deliberate choice: interactive browser use is expected in the main loop when the user enables the MCP server via `mcp_enable`.

## Re-check plan

One week after this change, re-run the same two SQL queries from the [2026-09-04 note](orchestrate-cost-rebalance-2026-09-04.md) against `~/.local/share/opencode/opencode.db`, using the trailing 7 days. Success criteria:

- Average context per orchestrate message (`avg_ctx_K`) stays below approximately 260K, confirming the `reserved` guardrail fires before the cliff.
- Zero messages have `tokens.total >= 272000`.
- The bash:task dispatch ratio returns to ≤1.2.
- Average output tokens per message is ≤250.
- 30-day-scaled cost lands in the $150–220 range; terra should beat the $205–258 sonnet-5 projection from the prior note given equivalent discipline.

If the bash:task ratio or output tokens do not improve, the model swap alone was insufficient and the prompt rewrite needs to become more directive.
