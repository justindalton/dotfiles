---
name: pr-watch
description: Full publish-and-watch workflow for orchestrate: push, open or reuse a GitHub PR, pr-prep, automated review, bot/reviewer triage, and babysit-pr watching with rebases until the PR is merged or closed. Use ONLY when orchestrate's publication decision selects it or the user explicitly asks to watch a PR.
---

# PR publish and watch

This skill runs after orchestrate has committed. Repository `AGENTS.md` PR
conventions (for example, draft PRs, labels, ready-for-review handoff, when to
stop watching, or whether to reply to bots) override these defaults where they
conflict.

Never ask confirmation before pushing, creating or reusing the branch PR, using
`pr-prep`, reviewing, fixing, rebasing, or watching. Push first, then create or
reuse the branch PR. Use draft mode when creating the PR if repository
instructions ask for it. Run `pr-prep`; inspect source edits via `implement`, run
warranted targeted validation, commit, and push changes. Review the complete PR
diff only after it is ready. Triage every review-agent, bot, and reviewer finding.
Delegate actionable fixes to `implement`, validate as warranted, commit/push, and
re-review affected areas when warranted. Give every dismissed finding an explicit
disposition. Human-authored comment replies require user approval, though code
fixes and thread resolution after a push may proceed automatically.

Use `babysit-pr` and keep watching until merged or closed, unless repository
instructions define an earlier stop condition. A push, green CI, quiet poll,
ready-to-merge state, or ordinary report does not end the watch. If a polling
batch ends while open, re-invoke `babysit-pr` in the same session. Triage every
subsequent review-agent, bot, and reviewer finding with explicit dispositions for
dismissals; fix actionable comments through the implement/validate/commit/push
loop, then continue watching. Never auto-merge or use a detached watcher.

Skip or stop only on explicit publication opt-out, interruption, a concrete
safety/user-help blocker (for example, unrelated dirty changes that cannot be
isolated, permissions, or unresolved product intent), or a repository-defined
stop condition. An explicit no-publication request means no PR, push, review, or
watch; report the skipped workflow.

## Rebase during PR babysitting

Keep the PR head current without rebasing every poll. At watcher start, fetch the
base and rebase the PR head onto its latest remote tip. During the watch, fetch
and compare the remote base after a long quiet period (for example 15 minutes),
when the base moves, and before declaring the PR ready to merge. If GitHub reports
conflicts or `DIRTY`, fetch and rebase immediately.

Before each rebase, require a clean intended working tree. Preserve unrelated
changes; never stash, reset, discard, or include them as a shortcut. If they
prevent a safe rebase, stop for user help. Never rebase or force-update the
default branch.

For routine conflicts, use repository evidence to dispatch an `implement` brief
scoped only to conflicted files, with an absolute `Owns:` list and conflict
details. The worker resolves and validates only that conflict. On failure,
dispatch a scoped implement follow-up; escalate repeated same-unit failure to
`implement-complex`. Never skip conflicts or use `review`/`verify` as an escape.

After rebase, run only warranted targeted validation, inspect the result, then
push the rewritten PR head with `--force-with-lease` only, never plain `--force`.
Immediately resume review/CI watching on the new SHA. Re-triage rewritten-SHA
feedback and retain every pending disposition; do not lose, duplicate, or silently
dismiss findings. Never auto-merge.

## Report

Report the PR URL and state, review findings and dispositions, terminal watch
state, latest feedback, and pending human approval. On interruption or blocker,
report incomplete work, watch state, blocker, and next action.
