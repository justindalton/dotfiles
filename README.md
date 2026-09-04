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

The Sol agents remain available for review and architecture escalation. The
architect is read-only and is reserved for material ambiguity, cross-module or
high-risk decisions, rule conflicts, and repeated Luna failures. Restart
opencode after configuration or plugin changes so updated links and settings
are loaded.

The installer is idempotent, but refuses to replace any existing non-matching
file, directory, or symlink. Resolve conflicts manually and run it again.

Provider and MCP authentication happens locally through opencode and the
relevant providers. Authentication state is never copied or committed. Supply
secrets through the providers' local environment variables or login flows;
never put secret values in this repository.

## Validation and updates

After changing configuration, validate JSON and shell syntax, inspect the diff,
and run the installer in an isolated temporary `HOME`. Pull updates, rerun the
installer, and restart opencode after configuration or plugin changes so the
new links and settings are loaded.
