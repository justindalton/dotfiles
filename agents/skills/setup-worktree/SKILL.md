---
name: setup-worktree
description: Set up an existing linked git worktree by copying gitignored env files (.env / .env.local / .env.dev, etc.) from the main worktree and installing dependencies. Use when a harness or git has already created a worktree that needs to be made ready to run. This skill does not create worktrees or branches.
---

# Setup worktree

Make an existing linked git worktree ready to run. Newly created worktrees are
missing the **gitignored** personal env files an app needs (for example,
app-level `.env.local` files and a root `.env.dev`) and may not have installed
dependencies. This skill closes both gaps without creating another worktree.

## Core principle

Detect existing isolation before changing anything. Resolve the **main**
worktree from `git rev-parse --git-common-dir`, verify that the target is a
linked worktree rather than the main checkout, and set up that target in place.

## Usage

```bash
~/.agents/skills/setup-worktree/scripts/setup-worktree.sh [worktree-path]
```

- `worktree-path` *(optional)* - existing linked worktree to set up. Defaults to
  the worktree containing the current directory.

## What it does

1. **Resolve the target and main worktrees** using git's own repository
   metadata. It aborts outside a repository or when pointed at the main
   checkout.
2. **Copy all gitignored env files** from the main worktree to matching relative
   paths in the target. It enumerates them with
   `git ls-files --others --ignored --exclude-standard --directory` and keeps
   only basenames matching `.env` / `.env.*`, so tracked files are never copied.
3. **Install dependencies** in the target worktree using its lockfile:
   `pnpm-lock.yaml` selects `pnpm install`, `yarn.lock` selects `yarn install`,
   `bun.lock` or `bun.lockb` selects `bun install`, and `package-lock.json`
   selects `npm install`. If there is no supported lockfile, installation is
   skipped with a message.

## Gotchas

- This skill only prepares an existing linked worktree. It never creates or
  checks out a branch and never calls `git worktree add`.
- Env files are gitignored, so they must be copied explicitly from the main
  worktree.
- Using `git ls-files --others --ignored` rather than a raw filesystem scan
  keeps the copy list aligned with `.gitignore` and avoids traversing large
  ignored directories such as `node_modules`.
- Running the script again refreshes the target's env files from the main
  worktree and reruns the dependency install.
