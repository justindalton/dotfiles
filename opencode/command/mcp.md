---
description: List or toggle configured MCP servers for this running OpenCode instance
---

Use the MCP toggle tools for the requested operation: `$ARGUMENTS`.

- With no arguments, call `mcp_list`.
- For a server name, call `mcp_enable` with that name.
- For `off <server-name>`, call `mcp_disable` with that name.

Report the tool's concise status to the user. Runtime changes are not persisted to config files.
