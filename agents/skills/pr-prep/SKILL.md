---
name: pr-prep
description: >-
  Prepare an open pull request for review: trim an over-long PR body, make sure
  the body covers everything actually changed on the branch, verify the title is
  accurate, and audit the branch's diff for oversized or low-value code comments
  and trim them. Use when the user asks to "prep", "clean up", "tidy", or
  "finalize" a PR, polish a PR description, or review/trim comments before review.
---

# PR prep

Polish the open PR for the current branch before review. Reuse the current PR
unless the caller names another. Update the PR metadata automatically; do not
ask for approval. Never merge the PR as part of this skill.

## 0. Gather context

```bash
gh pr view --json number,title,body,baseRefName,headRefName,url
BASE=origin/<baseRefName>            # usually origin/development or origin/main
git fetch origin <baseRefName>
git log "$BASE"..HEAD --oneline      # every commit on the branch
git diff "$BASE"...HEAD              # the full change set (use this everywhere below)
```

Infer `BASE` from the current PR; do not assume the default branch. Inspect
every commit and the complete three-dot diff. Scope every source check and
edit to added comment lines in `git diff "$BASE"...HEAD` — never touch code,
comments, or unrelated changes the branch did not introduce.

## 1. Body covers the whole branch

- Build a mental list of every meaningful change from the commits + diff, grouped by area/feature (not file-by-file).
- Check each is represented in the body. Add anything missing (new behavior, migrations, config/flags, breaking changes, follow-ups deliberately left out).
- Drop body claims that the diff doesn't support.

## 2. Trim body verbosity

A PR body is a reviewer's map, not a transcript. Keep it scannable.

- Keep: one-line **what & why**, key changes grouped as bullets, testing/verification, and any explicit reviewer call-outs or risks.
- Cut: line-by-line restatements of the diff, obvious implementation detail, boilerplate, repetition, and narration of how you got there.
- Prefer tight bullets over prose. Aim for roughly one screenful (~40 lines); longer is fine only when the change genuinely warrants it.

## 3. Title accuracy

- Reflects the branch's primary change; not stale relative to what shipped.
- Match the repo's convention (e.g. `type(scope): summary`, ticket id if the repo uses them — infer both from recent `git log`).
- Imperative, specific, no trailing punctuation.

## 4. Audit added comments in the diff

Look at **added** lines (`git diff "$BASE"...HEAD`) for comments. Apply this guidance, trimming or deleting in place:

- A comment should be **1–3 lines max**. Condense longer block/doc comments to the essential point; split only if truly necessary.
- A comment should appear **only before a complex or opaque logic block**, and explain the **why** (non-obvious constraint, workaround, surprising invariant) — not the what.
- Delete comments that restate the code, narrate obvious steps, are decorative/section banners, or are commented-out code (git remembers).
- Leave existing comments outside the branch's changes alone.

Apply these trims only to the added comment lines identified in the branch
diff. Existing comments outside those changed lines are out of scope.

If the caller is orchestrating work, it must delegate required source edits to
the `implement` worker; the orchestrator must not edit source files itself.
Standalone callers may edit the scoped source files directly.

Before any source edit, inspect `git status --short`. If the tree has
unrelated user changes, do not alter or commit them: stop source cleanup and
report the dirty-tree blocker. PR metadata-only cleanup may still proceed when
it is safe.

## 5. Apply

1. Prepare the accurate title and concise body from the complete branch
   history and diff, then run `gh pr edit <number> --title ... --body ...`.
2. If scoped comment trims were made, run only warranted targeted checks for
   the changed paths. Do not run repo-wide lint, typecheck, or formatting;
   pre-commit owns those checks. Markdown-only metadata changes need no tests.
3. Review the resulting source diff to ensure it contains only the scoped
   comment cleanup. Commit it with a focused message and push the current
   branch. Do not create an empty commit; if no source diff remains, skip the
   commit and push. Never commit unrelated dirty-tree changes.
4. Return a concise receipt covering the PR number/URL, final title, metadata
   update, source comment changes, commit/push status, checks run or skipped,
   and any blocker. Do not request approval.
