# Portable OpenCode configuration

This repository contains the portable, opencode-focused configuration used to
coordinate plans and delegate implementation and verification work. It is
public: never add credentials, authentication state, private configuration, or
machine-specific paths.

## Prerequisites and installation

Install Bash, Git, Node.js/npm, and opencode. The Playwright MCP wrapper also
requires `shasum` and `cut`. Clone this repository, then run:

```sh
git clone https://github.com/justindalton/dotfiles.git ~/code/dotfiles
cd ~/code/dotfiles
./bin/install-opencode
```

The installer creates `$HOME/.config/opencode` and links these tracked items
individually: `opencode.json`, `opencode-tools.json`, `tui.jsonc`, `zen.json`,
`herdr-tui-session.js`, `agent/`, `command/`, `plugins/`, and `bin/`. Existing
generated runtime files such as `node_modules` and `figwright-plugin` are left
alone.

The tracked default profile is lean: every configured MCP is disabled at
startup. The runtime `mcp-toggle` plugin is the primary interactive mechanism;
use the `/mcp` command to inspect or change the current OpenCode instance:

```text
/mcp                 # list configured servers and live state
/mcp figma           # enable figma for this instance
/mcp off figma       # disconnect figma without deleting its config
```

Runtime toggles are not written to disk. For a batch or non-interactive
full-tool session, launch opencode with the overlay that re-enables its MCPs:

```sh
OPENCODE_CONFIG="$HOME/.config/opencode/opencode-tools.json" opencode
```

## OpenCode Zen profile

The default profile uses direct Anthropic and OpenAI providers. Run
`~/.config/opencode/bin/opencode-zen` to use the same agents through OpenCode
Zen with identical model IDs. Authenticate once with `opencode auth login`
(choose OpenCode Zen), or set `OPENCODE_API_KEY`. For convenience, add
`alias ocz="$HOME/.config/opencode/bin/opencode-zen"` to your shell.

Agent models live in `opencode.json` under `agent.<name>.model`, not in agent
frontmatter, so overlays can remap them. When changing an agent's model, update
both `opencode.json` and `zen.json`.

The Sol agents remain available for review and architecture decisions. The
read-only architect may be consulted when an independent opinion is genuinely
helpful for a design or tradeoff decision; routine consultation is optional,
and orchestrate remains the decision-maker. The bundled `code-simplifier` skill
provides behavior-preserving maintainability guidance, and the review agent
uses it during every review. The bundled `pr-watch` skill handles pull-request
publication and follow-through when applicable. Restart opencode after
configuration or plugin changes so updated links and settings are loaded.

Implementation is split between `implement` (gpt-6-luna, straightforward
scoped work) and `implement-complex` (claude-opus-5-5, complex or escalated
work), selected per brief by orchestrate.

The installer is idempotent, but refuses to replace any existing non-matching
file, directory, or symlink. Resolve conflicts manually and run it again.

Provider and MCP authentication happens locally through opencode and the
relevant providers. Authentication state is never copied or committed. Supply
secrets through the providers' local environment variables or login flows;
never put secret values in this repository.

## Publication modes

After committing, orchestrate selects one publication mode; the first match
wins:

1. Follow an explicit publication instruction in the session.
2. Follow the repository's `AGENTS.md` publication, PR, or CI conventions,
   including partial conventions such as direct pushes to `main`.
3. Use `pr-watch` to push, open or reuse a PR, run `pr-prep`, request review,
   and use `babysit-pr` until merged or closed when the repository has a GitHub
   `origin` remote and a CI configuration (GitHub Actions, Buildkite,
   CircleCI, GitLab CI, Jenkins, Azure Pipelines, or Bitbucket Pipelines).
4. Otherwise, commit only and report the commit SHA and skipped steps.

Ask for publication in-session to override the repository's default mode.

## Validation and updates

After changing configuration, validate JSON and shell syntax, inspect the diff,
and run the installer in an isolated temporary `HOME`. Pull updates, rerun the
installer, and restart opencode after configuration or plugin changes so the
new links and settings are loaded.
