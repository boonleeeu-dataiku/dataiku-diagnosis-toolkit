// IMPORTANT: this process talks MCP over stdio, so stdout is the JSON-RPC wire. Never write to
// stdout (no console.log, here or in any dependency) - all diagnostics must go to console.error.
import { readFileSync } from "node:fs";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerResources } from "./resources.js";
import { registerRunOrientTool } from "./tools/run-orient.js";

// Single source of truth for the reported version: dist/index.js -> ../package.json.
const { version } = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as {
  version: string;
};

async function main() {
  const server = new McpServer({ name: "dataiku-diagnosis-reader", version });

  registerResources(server);
  registerRunOrientTool(server);

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error starting dataiku-diagnosis-reader MCP server:", err);
  process.exit(1);
});
