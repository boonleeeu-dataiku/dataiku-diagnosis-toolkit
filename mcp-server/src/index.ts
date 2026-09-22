// IMPORTANT: this process talks MCP over stdio, so stdout is the JSON-RPC wire. Never write to
// stdout (no console.log, here or in any dependency) - all diagnostics must go to console.error.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerResources } from "./resources.js";
import { registerRunOrientTool } from "./tools/run-orient.js";
import { registerSafeReadTool } from "./tools/safe-read.js";

async function main() {
  const server = new McpServer({ name: "dataiku-diagnosis-reader", version: "0.1.0" });

  registerResources(server);
  registerRunOrientTool(server);
  registerSafeReadTool(server);

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error starting dataiku-diagnosis-reader MCP server:", err);
  process.exit(1);
});
