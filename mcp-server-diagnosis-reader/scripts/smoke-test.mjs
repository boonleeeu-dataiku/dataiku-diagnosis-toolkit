#!/usr/bin/env node
// Quick regression check for the built server: initialize -> resources/list -> tools/list ->
// tools/call run_orient, all over raw JSON-RPC via stdio. Defaults to the committed synthetic
// fixture bundle; pass a bundle root as a CLI argument to target another one. Never hardcode a
// real bundle path here.
//
// Usage: node scripts/smoke-test.mjs [bundle_root]

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const bundleRoot = process.argv[2] ?? path.resolve(here, "..", "test", "fixtures", "bundles", "synthetic_design");
const serverEntry = path.resolve(here, "..", "dist", "index.js");

const child = spawn("node", [serverEntry], { stdio: ["pipe", "pipe", "inherit"] });

let buffer = "";
const pending = new Map();
let nextId = 1;

child.stdout.on("data", (chunk) => {
  buffer += chunk.toString("utf8");
  let idx;
  while ((idx = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, idx);
    buffer = buffer.slice(idx + 1);
    if (!line.trim()) continue;
    const msg = JSON.parse(line);
    const resolver = pending.get(msg.id);
    if (resolver) {
      pending.delete(msg.id);
      resolver(msg);
    }
  }
});

function send(method, params) {
  const id = nextId++;
  const req = { jsonrpc: "2.0", id, method, params };
  child.stdin.write(JSON.stringify(req) + "\n");
  return new Promise((resolve) => pending.set(id, resolve));
}

function assert(cond, message) {
  if (!cond) {
    console.error(`FAIL: ${message}`);
    child.kill();
    process.exit(1);
  }
  console.log(`ok: ${message}`);
}

async function main() {
  await send("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "smoke-test", version: "0.0.0" },
  });
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");

  const resources = await send("resources/list", {});
  assert(resources.result?.resources?.length === 9, `resources/list returns 9 resources (got ${resources.result?.resources?.length})`);

  const tools = await send("tools/list", {});
  const toolNames = (tools.result?.tools ?? []).map((t) => t.name).sort();
  assert(
    JSON.stringify(toolNames) === JSON.stringify(["run_orient", "safe_read"]),
    `tools/list returns exactly run_orient and safe_read (got ${JSON.stringify(toolNames)})`,
  );

  const orient = await send("tools/call", { name: "run_orient", arguments: { bundle_root: bundleRoot } });
  assert(orient.result?.isError !== true, `run_orient succeeds against ${bundleRoot}`);

  console.log("All smoke tests passed.");
  child.kill();
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  child.kill();
  process.exit(1);
});
