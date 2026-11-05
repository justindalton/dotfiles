function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

const EMPTY_INPUT = {
  type: "object",
  properties: {},
  additionalProperties: false,
};

function nameInput(description) {
  return {
    type: "object",
    properties: {
      name: { type: "string", minLength: 1 },
    },
    required: ["name"],
    additionalProperties: false,
    description,
  };
}

export default {
  id: "dotfiles.mcp-toggle",
  async setup(ctx) {
    const disabledByName = new Map();

    await ctx.mcp.transform((editor) => {
      const names = new Set(editor.list().map((server) => server.name));
      for (const [name, disabled] of disabledByName) {
        if (!names.has(name)) continue;
        editor.update(name, (server) => {
          server.disabled = disabled;
        });
      }
    });

    await ctx.tool.transform((editor) => {
      editor.add({
        name: "mcp_list",
        description: "List configured MCP servers and their current live connection state.",
        input: EMPTY_INPUT,
        async execute() {
          try {
            const { data: servers } = await ctx.mcp.list();
            if (servers.length === 0) return { content: "No configured MCP servers." };

            return {
              content: servers
                .map((server) => `${server.name}: configured, ${server.status.status}`)
                .sort((a, b) => a.localeCompare(b))
                .join("\n"),
            };
          } catch (error) {
            return { content: `Could not list MCP servers: ${errorMessage(error)}` };
          }
        },
      });

      editor.add({
        name: "mcp_enable",
        description:
          "Enable a configured MCP server for this running OpenCode instance without changing config files.",
        input: nameInput("Configured MCP server name"),
        async execute({ name }) {
          try {
            const { data: servers } = await ctx.mcp.list();
            if (!servers.some((server) => server.name === name)) {
              return { content: `Unknown configured MCP server: ${name}.` };
            }
            disabledByName.set(name, false);
            await ctx.mcp.reload();
            return { content: `MCP server ${name} enabled for this OpenCode instance.` };
          } catch (error) {
            return { content: `Could not enable MCP server ${name}: ${errorMessage(error)}` };
          }
        },
      });

      editor.add({
        name: "mcp_disable",
        description:
          "Disconnect a configured MCP server for this running OpenCode instance without deleting its config.",
        input: nameInput("Configured MCP server name"),
        async execute({ name }) {
          try {
            const { data: servers } = await ctx.mcp.list();
            if (!servers.some((server) => server.name === name)) {
              return { content: `Unknown configured MCP server: ${name}.` };
            }
            disabledByName.set(name, true);
            await ctx.mcp.reload();
            return { content: `MCP server ${name} disconnected; its configuration was kept.` };
          } catch (error) {
            return { content: `Could not disable MCP server ${name}: ${errorMessage(error)}` };
          }
        },
      });
    });
  },
};
