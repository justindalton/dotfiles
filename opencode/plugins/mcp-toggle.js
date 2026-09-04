function responseData(response) {
  return response && typeof response === "object" && "data" in response
    ? response.data
    : response;
}

function configuredServers(config) {
  const mcp = config && typeof config === "object" ? config.mcp : undefined;
  if (!mcp || typeof mcp !== "object" || Array.isArray(mcp)) {
    return { servers: {}, malformed: true };
  }

  const servers = {};
  for (const [name, value] of Object.entries(mcp)) {
    servers[name] = value;
  }
  return { servers, malformed: false };
}

async function getServers(client) {
  const result = responseData(await client.config.get());
  return configuredServers(result);
}

function validName(name) {
  return typeof name === "string" && name.trim().length > 0;
}

function connectionConfig(config) {
  const copy = { ...config };
  // Startup-only state is not needed by the runtime add endpoint and some
  // OpenCode versions reject it there.
  delete copy.enabled;
  return copy;
}

function validServerConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) return false;
  if (config.type === "local") {
    return (
      Array.isArray(config.command) &&
      config.command.length > 0 &&
      config.command.every((part) => typeof part === "string")
    );
  }
  return config.type === "remote" && typeof config.url === "string" && config.url.length > 0;
}

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

export const McpTogglePlugin = async ({ client }) => ({
  tool: {
    mcp_enable: {
      description:
        "Enable a configured MCP server for this running OpenCode instance without changing config files.",
      args: {
        name: {
          type: "string",
          minLength: 1,
          description: "Configured MCP server name",
        },
      },
      async execute({ name }) {
        if (!validName(name)) return "MCP server name is required.";
        try {
          const { servers, malformed } = await getServers(client);
          if (malformed) return "MCP configuration is missing or malformed.";
          if (!Object.hasOwn(servers, name)) {
            return `Unknown configured MCP server: ${name}.`;
          }
          const config = servers[name];
          if (!validServerConfig(config)) {
            return `MCP server ${name} has malformed configuration.`;
          }
          await client.mcp.add({
            body: { name, config: connectionConfig(config) },
          });
          return `MCP server ${name} enabled for this OpenCode instance.`;
        } catch (error) {
          return `Could not enable MCP server ${name}: ${errorMessage(error)}`;
        }
      },
    },

    mcp_disable: {
      description:
        "Disconnect a configured MCP server for this running OpenCode instance without deleting its config.",
      args: {
        name: {
          type: "string",
          minLength: 1,
          description: "Configured MCP server name",
        },
      },
      async execute({ name }) {
        if (!validName(name)) return "MCP server name is required.";
        try {
          const { servers, malformed } = await getServers(client);
          if (malformed) return "MCP configuration is missing or malformed.";
          if (!Object.hasOwn(servers, name)) {
            return `Unknown configured MCP server: ${name}.`;
          }
          if (!validServerConfig(servers[name])) {
            return `MCP server ${name} has malformed configuration.`;
          }
          await client.mcp.disconnect({ path: { name } });
          return `MCP server ${name} disconnected; its configuration was kept.`;
        } catch (error) {
          return `Could not disable MCP server ${name}: ${errorMessage(error)}`;
        }
      },
    },

    mcp_list: {
      description: "List configured MCP servers and their current live connection state.",
      args: {},
      async execute() {
        try {
          const [{ servers, malformed }, statusResponse] = await Promise.all([
            getServers(client),
            client.mcp.status(),
          ]);
          if (malformed) return "MCP configuration is missing or malformed.";
          const statuses = responseData(statusResponse);
          if (!statuses || typeof statuses !== "object" || Array.isArray(statuses)) {
            return "MCP live status is malformed.";
          }
          const names = Object.keys(servers).sort();
          if (names.length === 0) return "No configured MCP servers.";
          return names
            .map((name) => {
              const status = statuses[name];
              const state = validServerConfig(servers[name])
                ? (status?.status ?? "not registered")
                : "malformed config";
              return `${name}: configured, ${state}`;
            })
            .join("\n");
        } catch (error) {
          return `Could not list MCP servers: ${errorMessage(error)}`;
        }
      },
    },
  },
});

export default McpTogglePlugin;
