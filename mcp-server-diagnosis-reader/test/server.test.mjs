// End-to-end tool/resource behavior over real stdio JSON-RPC against the built server.

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import path from "node:path";
import { AUTOMATION_BUNDLE, DESIGN_BUNDLE, McpClient, SERVER_ROOT, SKILL_ROOT, makeTempBundle } from "./helpers.mjs";

let client;
before(async () => {
  client = await new McpClient().initialize();
});
after(() => client.close());

// --- Registration --------------------------------------------------------------------------

test("initialize reports the package.json version", async () => {
  const pkg = JSON.parse(await fs.readFile(path.join(SERVER_ROOT, "package.json"), "utf8"));
  assert.equal(client.serverInfo?.version, pkg.version);
});

test("tools/list exposes exactly run_orient", async () => {
  const res = await client.send("tools/list", {});
  assert.deepEqual(res.result.tools.map((t) => t.name).sort(), ["run_orient"]);
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
