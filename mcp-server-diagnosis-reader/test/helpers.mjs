// Shared test helpers: fixture paths, and a minimal JSON-RPC-over-stdio client for the built
// server (same wire approach as scripts/smoke-test.mjs). Tests run against dist/, so run
// `npm run build` first (`npm test` does this for you).

import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const SERVER_ROOT = path.resolve(here, "..");
export const SERVER_ENTRY = path.join(SERVER_ROOT, "dist", "index.js");
export const FIXTURE_BUNDLES = path.join(here, "fixtures", "bundles");
export const DESIGN_BUNDLE = path.join(FIXTURE_BUNDLES, "synthetic_design");
export const AUTOMATION_BUNDLE = path.join(FIXTURE_BUNDLES, "synthetic_automation");
// Mirrors src/lib/skill-location.ts: the spawned server inherits DATAIKU_SKILL_DIR too, so tests and
// server agree on where the skill lives (a sibling here; skills/dataiku-diagnosis-reader/ in the
// dataiku-diagnosis-toolkit plugin, which sets the variable).
export const SKILL_ROOT = process.env.DATAIKU_SKILL_DIR
  ? path.resolve(process.env.DATAIKU_SKILL_DIR)
  : path.resolve(SERVER_ROOT, "..", "dataiku-diagnosis-reader");

export class McpClient {
  constructor(env = {}) {
    this.child = spawn("node", [SERVER_ENTRY], {
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, ...env },
    });
    this.buffer = "";
    this.pending = new Map();
    this.nextId = 1;
    this.child.stdout.on("data", (chunk) => {
      this.buffer += chunk.toString("utf8");
      let idx;
      while ((idx = this.buffer.indexOf("\n")) !== -1) {
        const line = this.buffer.slice(0, idx);
        this.buffer = this.buffer.slice(idx + 1);
        if (!line.trim()) continue;
        const msg = JSON.parse(line);
        const resolve = this.pending.get(msg.id);
        if (resolve) {
          this.pending.delete(msg.id);
          resolve(msg);
        }
      }
    });
  }

  send(method, params) {
    const id = this.nextId++;
    this.child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    return new Promise((resolve) => this.pending.set(id, resolve));
  }

  async initialize() {
    const res = await this.send("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "node-test", version: "0.0.0" },
    });
    this.serverInfo = res.result?.serverInfo;
    this.child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
    return this;
  }

  /** Calls a tool and returns { isError, text } from its single text content block. */
  async callTool(name, args) {
    const msg = await this.send("tools/call", { name, arguments: args });
    if (msg.error) return { isError: true, text: msg.error.message, protocolError: true };
    return { isError: msg.result?.isError === true, text: msg.result?.content?.[0]?.text ?? "" };
  }

  close() {
    this.child.kill();
  }
}

/** Fresh temp directory shaped like a bundle root (diag.txt + timings.txt present). */
export async function makeTempBundle() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "reader-test-"));
  await fs.writeFile(path.join(dir, "diag.txt"), "synthetic\n");
  await fs.writeFile(path.join(dir, "timings.txt"), "synthetic\n");
  return dir;
}
