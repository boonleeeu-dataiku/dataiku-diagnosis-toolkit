import path from "node:path";
import { promises as fs } from "node:fs";
import { ToolInputError } from "./errors.js";

/** Resolves relativePath against root and refuses anything that escapes root, including via a
 * symlink inside the bundle that points outside it. Returns the resolved, symlink-free absolute
 * path. Throws ToolInputError (never a raw fs error) on any traversal attempt. */
export async function resolveWithinRoot(root: string, relativePath: string): Promise<string> {
  if (path.isAbsolute(relativePath)) {
    throw new ToolInputError("relative_path must be relative, not absolute.");
  }

  let realRoot: string;
  try {
    realRoot = await fs.realpath(root);
  } catch {
    throw new ToolInputError(`bundle_root does not exist or is not accessible: ${root}`);
  }

  const candidate = path.resolve(realRoot, relativePath);

  // The candidate itself might not exist yet as a real path resolves symlinks along the way;
  // fall back to the un-resolved candidate only if realpath fails, then re-check containment.
  const real = await fs.realpath(candidate).catch(() => candidate);

  if (real !== realRoot && !real.startsWith(realRoot + path.sep)) {
    throw new ToolInputError(`relative_path escapes bundle_root: ${relativePath}`);
  }

  return real;
}
