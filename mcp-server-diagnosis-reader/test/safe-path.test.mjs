import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import path from "node:path";
import { resolveWithinRoot } from "../dist/lib/safe-path.js";
import { resolveBundleRoot } from "../dist/lib/bundle-root.js";
import { ToolInputError } from "../dist/lib/errors.js";
import { DESIGN_BUNDLE, makeTempBundle } from "./helpers.mjs";

test("resolves a normal relative path inside the root", async () => {
  const real = await resolveWithinRoot(DESIGN_BUNDLE, "data_dataiku/design/install.ini");
  assert.equal(real, await fs.realpath(path.join(DESIGN_BUNDLE, "data_dataiku/design/install.ini")));
});

test("rejects an absolute relative_path", async () => {
  await assert.rejects(resolveWithinRoot(DESIGN_BUNDLE, "/etc/passwd"), ToolInputError);
});

test("rejects ../ traversal out of the root", async () => {
  await assert.rejects(resolveWithinRoot(DESIGN_BUNDLE, "../synthetic_automation/diag.txt"), /escapes bundle_root/);
});

test("rejects traversal that only escapes partway", async () => {
  await assert.rejects(resolveWithinRoot(DESIGN_BUNDLE, "data_dataiku/../../x"), /escapes bundle_root/);
});

test("rejects a sibling directory sharing the root's name prefix", async () => {
  // root ".../bundle" must not accept ".../bundle-evil/x" via a naive startsWith check
  const root = await makeTempBundle();
  const evil = `${root}-evil`;
  await fs.mkdir(evil, { recursive: true });
  await fs.writeFile(path.join(evil, "x"), "secret");
  await assert.rejects(resolveWithinRoot(root, `../${path.basename(evil)}/x`), /escapes bundle_root/);
});

test("rejects a symlink inside the bundle that points outside it", async () => {
  const root = await makeTempBundle();
  const outside = await makeTempBundle();
  await fs.writeFile(path.join(outside, "secret.txt"), "secret");
  await fs.symlink(path.join(outside, "secret.txt"), path.join(root, "link.txt"));
  await assert.rejects(resolveWithinRoot(root, "link.txt"), /escapes bundle_root/);
});

test("allows a symlink that stays inside the bundle", async () => {
  const root = await makeTempBundle();
  await fs.symlink(path.join(root, "diag.txt"), path.join(root, "alias.txt"));
  assert.equal(await resolveWithinRoot(root, "alias.txt"), await fs.realpath(path.join(root, "diag.txt")));
});

test("rejects a missing bundle root", async () => {
  await assert.rejects(resolveWithinRoot("/definitely/not/here", "diag.txt"), /does not exist/);
});

test("resolveBundleRoot requires an absolute path", () => {
  assert.throws(() => resolveBundleRoot("relative/bundle"), /must be an absolute path/);
});

test("resolveBundleRoot falls back to DATAIKU_BUNDLE_ROOT, else errors", () => {
  const saved = process.env.DATAIKU_BUNDLE_ROOT;
  try {
    process.env.DATAIKU_BUNDLE_ROOT = DESIGN_BUNDLE;
    assert.equal(resolveBundleRoot(undefined), DESIGN_BUNDLE);
    delete process.env.DATAIKU_BUNDLE_ROOT;
    assert.throws(() => resolveBundleRoot(undefined), /DATAIKU_BUNDLE_ROOT is not set/);
  } finally {
    if (saved === undefined) delete process.env.DATAIKU_BUNDLE_ROOT;
    else process.env.DATAIKU_BUNDLE_ROOT = saved;
  }
});
