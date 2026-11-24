#!/usr/bin/env bash
set -euo pipefail

# setup-worktree.sh [worktree-path]
#
# Copies gitignored env files from the main worktree into an existing linked
# worktree and installs dependencies there.

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: setup-worktree.sh [worktree-path]

  worktree-path  Existing linked worktree to set up. Defaults to the worktree
                 containing the current directory.
USAGE
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "error: expected at most one worktree path" >&2
  exit 1
fi

REQUESTED_PATH="${1:-$PWD}"
TARGET="$(git -C "$REQUESTED_PATH" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "error: not inside a git worktree: $REQUESTED_PATH" >&2
  exit 1
}
TARGET="$(cd "$TARGET" && pwd -P)"

# git-common-dir points at the main checkout's .git directory even when this
# script runs from a linked worktree.
COMMON_DIR="$(git -C "$TARGET" rev-parse --git-common-dir)"
COMMON_DIR="$(cd "$TARGET" && cd "$COMMON_DIR" && pwd -P)"
MAIN="$(dirname "$COMMON_DIR")"

if [[ "$TARGET" == "$MAIN" ]]; then
  echo "error: target is the main worktree, not a linked worktree: $TARGET" >&2
  exit 1
fi

if [[ ! -d "$MAIN" ]]; then
  echo "error: main worktree is unavailable: $MAIN" >&2
  exit 1
fi

echo "Copying gitignored env files from $MAIN..."
copied=0
while IFS= read -r rel; do
  case "$(basename "$rel")" in
    .env|.env.*) ;;
    *) continue ;;
  esac
  src="$MAIN/$rel"
  dest="$TARGET/$rel"
  [[ -f "$src" ]] || continue
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  copied $rel"
  copied=$((copied + 1))
done < <(git -C "$MAIN" ls-files --others --ignored --exclude-standard --directory)

if [[ "$copied" -eq 0 ]]; then
  echo "  (no gitignored env files found in main worktree)"
fi

# Install dependencies after the env is in place so package lifecycle scripts
# see the same configuration as the application.
if [[ -f "$TARGET/pnpm-lock.yaml" ]]; then
  echo "Installing dependencies (pnpm install)..."
  (cd "$TARGET" && pnpm install)
elif [[ -f "$TARGET/yarn.lock" ]]; then
  echo "Installing dependencies (yarn install)..."
  (cd "$TARGET" && yarn install)
elif [[ -f "$TARGET/bun.lock" || -f "$TARGET/bun.lockb" ]]; then
  echo "Installing dependencies (bun install)..."
  (cd "$TARGET" && bun install)
elif [[ -f "$TARGET/package-lock.json" ]]; then
  echo "Installing dependencies (npm install)..."
  (cd "$TARGET" && npm install)
else
  echo "Skipping dependency install: no supported package-manager lockfile found in $TARGET"
fi

echo
echo "Worktree ready:"
echo "  $TARGET"
