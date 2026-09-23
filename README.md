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
individually: `opencode.json`, `opencode-tools.json`, `tui.jsonc`,
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

The Sol agents remain available for review and architecture decisions. The
read-only architect may be consulted when an independent opinion is genuinely
helpful for a design or tradeoff decision; routine consultation is optional,
and orchestrate remains the decision-maker. The bundled `code-simplifier` skill
provides behavior-preserving maintainability guidance, and the review agent
uses it during every review. Restart opencode after configuration or plugin
changes so updated links and settings are loaded.

The installer is idempotent, but refuses to replace any existing non-matching
file, directory, or symlink. Resolve conflicts manually and run it again.

Provider and MCP authentication happens locally through opencode and the
relevant providers. Authentication state is never copied or committed. Supply
secrets through the providers' local environment variables or login flows;
never put secret values in this repository.

### Jev compaction pilot

`jev-compaction.ts` is auto-discovered from the linked global `plugins/`
directory; it is intentionally not listed in `opencode.json`. Set
`TYPESAFE_API_KEY` in your local environment (never commit or share it), then
restart OpenCode. Before ordinary requests and before both manual `/compact`
and automatic native compaction, Jev filters eligible historical tool calls and
their results. The native compaction agent still writes the summary.

The pinned upstream revision is
`quinnjr/opencode-jev-compaction@9181265438237451d727acc529340096b80e5127`.
Local defaults are a 100,000-token threshold, 12 preserved recent messages,
0.35 keep threshold, 1,000-character result previews, and 5,000 ms per-request
and total timeouts. Use `JEV_COMPACTION_DISABLED=1` to disable it,
`JEV_COMPACTION_DEBUG=1` for diagnostics, and these environment variables to
tune it: `JEV_COMPACTION_THRESHOLD`, `JEV_PRESERVE_RECENT`,
`JEV_KEEP_THRESHOLD`, `JEV_TRUNCATE_HEAD_CHARS`, `JEV_TIMEOUT_MS`,
`JEV_TOTAL_TIMEOUT_MS`, `JEV_MAX_CONCURRENT`, `JEV_STATE_INCLUDE_TEXT`,
`JEV_MODEL`, and `JEV_BASE_URL`.

Requests send data to TypeSafe: abridged user, assistant, and reasoning text,
plus tool inputs and metadata; tool-result bodies are not sent. The plugin
fails open: missing credentials, unavailable or slow Jev requests, and fitting
failures leave the conversation unchanged.

## Validation and updates

After changing configuration, validate JSON and shell syntax, inspect the diff,
and run the installer in an isolated temporary `HOME`. Pull updates, rerun the
installer, and restart opencode after configuration or plugin changes so the
new links and settings are loaded.
