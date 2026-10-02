// End-to-end tool/resource behavior over real stdio JSON-RPC against the built server.

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import path from "node:path";
import { DEFAULT_MAX_BYTES } from "../dist/lib/limits.js";
import { AUTOMATION_BUNDLE, DESIGN_BUNDLE, McpClient, SERVER_ROOT, SKILL_ROOT, makeTempBundle } from "./helpers.mjs";

let client;
before(async () => {
  client = await new McpClient().initialize();
});
after(() => client.close());

const read = (args) => client.callTool("safe_read", { bundle_root: DESIGN_BUNDLE, ...args });

// --- Registration --------------------------------------------------------------------------

test("initialize reports the package.json version", async () => {
  const pkg = JSON.parse(await fs.readFile(path.join(SERVER_ROOT, "package.json"), "utf8"));
  assert.equal(client.serverInfo?.version, pkg.version);
});

test("tools/list exposes exactly run_orient and safe_read", async () => {
  const res = await client.send("tools/list", {});
  assert.deepEqual(res.result.tools.map((t) => t.name).sort(), ["run_orient", "safe_read"]);
});

test("resources/list covers SKILL.md and every references/*.md, and nothing missing on disk", async () => {
  const res = await client.send("resources/list", {});
  const uris = res.result.resources.map((r) => r.uri).sort();
  const refs = (await fs.readdir(path.join(SKILL_ROOT, "references"))).filter((f) => f.endsWith(".md"));
  const expected = ["dataiku-skill://SKILL.md", ...refs.map((f) => `dataiku-skill://references/${f}`)].sort();
  assert.deepEqual(uris, expected, "resources.ts RESOURCE_FILES is out of sync with references/");
});

test("every resource can be read", async () => {
  const res = await client.send("resources/list", {});
  for (const { uri } of res.result.resources) {
    const msg = await client.send("resources/read", { uri });
    assert.ok(msg.result?.contents?.[0]?.text?.length > 0, `empty or failed read for ${uri}`);
  }
});

// --- safe_read -----------------------------------------------------------------------------

test("safe_read returns a small file with a header", async () => {
  const { isError, text } = await read({ relative_path: "data_dataiku/design/install.ini" });
  assert.equal(isError, false);
  assert.match(text, /^\[safe_read\] file=data_dataiku\/design\/install.ini .* truncated=false/);
  assert.match(text, /nodetype = design/);
});

test("safe_read honors max_lines without a pattern", async () => {
  const { text } = await read({ relative_path: "data_dataiku/design/install.ini", max_lines: 2 });
  assert.match(text, /lines_returned=2 truncated=true\(hit max_lines\)/);
});

test("safe_read pattern filters lines with 1-based line numbers", async () => {
  const { text } = await read({ relative_path: "data_dataiku/design/run/backend.log", pattern: "ERROR" });
  assert.match(text, /matches_returned=1 truncated=false/);
  assert.match(text, /\n2: .*Synthetic job failure one/);
});

test("safe_read pattern_flags are applied", async () => {
  const { text } = await read({ relative_path: "data_dataiku/design/run/backend.log", pattern: "error", pattern_flags: "i" });
  assert.match(text, /matches_returned=2/);
});

test("safe_read rejects an invalid regex", async () => {
  const { isError, text } = await read({ relative_path: "diag.txt", pattern: "(" });
  assert.equal(isError, true);
  assert.match(text, /Invalid regex pattern/);
});

test("safe_read refuses traversal outside the bundle", async () => {
  const { isError, text } = await read({ relative_path: "../synthetic_automation/diag.txt" });
  assert.equal(isError, true);
  assert.match(text, /escapes bundle_root/);
});

test("safe_read refuses a directory", async () => {
  const { isError, text } = await read({ relative_path: "data_dataiku" });
  assert.equal(isError, true);
  assert.match(text, /is a directory/);
});

test("safe_read reports a missing file as a tool error, not a crash", async () => {
  const { isError, text } = await read({ relative_path: "nope.txt" });
  assert.equal(isError, true);
  assert.match(text, /Could not stat nope.txt/);
});

test("safe_read refuses an oversized file without a pattern, but greps it with one", async () => {
  const root = await makeTempBundle();
  const line = "x".repeat(99) + "\n";
  const big = line.repeat(Math.ceil((DEFAULT_MAX_BYTES + 1) / line.length)) + "NEEDLE here\n";
  await fs.writeFile(path.join(root, "big.log"), big);

  const refused = await client.callTool("safe_read", { bundle_root: root, relative_path: "big.log" });
  assert.equal(refused.isError, true);
  assert.match(refused.text, /exceeds max_bytes/);

  const grepped = await client.callTool("safe_read", { bundle_root: root, relative_path: "big.log", pattern: "NEEDLE" });
  assert.equal(grepped.isError, false);
  assert.match(grepped.text, /matches_returned=1/);
});

test("safe_read refuses a binary file without a pattern", async () => {
  const root = await makeTempBundle();
  await fs.writeFile(path.join(root, "blob.bin"), Buffer.from([0x50, 0x4b, 0x00, 0x01]));
  const { isError, text } = await client.callTool("safe_read", { bundle_root: root, relative_path: "blob.bin" });
  assert.equal(isError, true);
  assert.match(text, /appears to be a binary file/);
});

test("safe_read schema rejects max_lines above the hard cap", async () => {
  const res = await read({ relative_path: "diag.txt", max_lines: 1_000_000 });
  assert.equal(res.isError, true);
});

test("safe_read requires an absolute bundle_root", async () => {
  const { isError, text } = await client.callTool("safe_read", { bundle_root: "relative", relative_path: "diag.txt" });
  assert.equal(isError, true);
  assert.match(text, /must be an absolute path/);
});

// --- run_orient ----------------------------------------------------------------------------

test("run_orient reports node type, version and key files for a design bundle", async () => {
  const { isError, text } = await client.callTool("run_orient", { bundle_root: DESIGN_BUNDLE });
  assert.equal(isError, false, text);
  assert.match(text, /nodetype: design/);
  assert.match(text, /nodeid:\s+synthetic-design-01/);
  assert.match(text, /product_version: 14\.4\.3/);
  assert.match(text, /\[present\] dmesg\.txt/);
  assert.match(text, /\[absent\]\s+stacks\.txt/);
  assert.match(text, /\[present\] run\/sanity-check\.json/);
  assert.match(text, /\[present\] run\/hs_err_pid\*\.log \(1 file\(s\)\)/);
  assert.match(text, /active-bundle\.json found under config\/projects\/: 0/);
});

test("run_orient picks up bundle-activation signals on an automation bundle", async () => {
  const { isError, text } = await client.callTool("run_orient", { bundle_root: AUTOMATION_BUNDLE });
  assert.equal(isError, false, text);
  assert.match(text, /nodetype: automation/);
  assert.match(text, /product_version: 13\.2\.0/);
  assert.match(text, /active-bundle\.json found under config\/projects\/: 1/);
  assert.match(text, /acode-envs\/ has content/);
});

test("run_orient rejects a directory that isn't a bundle root", async () => {
  const dir = path.dirname(DESIGN_BUNDLE);
  const { isError, text } = await client.callTool("run_orient", { bundle_root: dir });
  assert.equal(isError, true);
  assert.match(text, /does not look like a diagnosis bundle root/);
});

test("run_orient reports a bundle with no install.ini", async () => {
  const root = await makeTempBundle();
  const { isError, text } = await client.callTool("run_orient", { bundle_root: root });
  assert.equal(isError, false, text);
  assert.match(text, /Could not find install\.ini/);
});

test("run_orient fails clearly when orient.sh can't be found", async () => {
  const other = await new McpClient({ DATAIKU_SKILL_DIR: "/definitely/not/here" }).initialize();
  try {
    const { isError, text } = await other.callTool("run_orient", { bundle_root: DESIGN_BUNDLE });
    assert.equal(isError, true);
    assert.match(text, /Could not find orient\.sh/);
  } finally {
    other.close();
  }
});
