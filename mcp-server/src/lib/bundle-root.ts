import path from "node:path";
import { ToolInputError } from "./errors.js";

/** Resolves the bundle_root a tool should operate on: the explicit per-call argument if given,
 * otherwise the DATAIKU_BUNDLE_ROOT env var. There is no other fallback — bundle targeting is
 * always explicit, never inferred. */
export function resolveBundleRoot(input?: string): string {
  const root = input ?? process.env.DATAIKU_BUNDLE_ROOT;
  if (!root) {
    throw new ToolInputError(
      "bundle_root was not provided and DATAIKU_BUNDLE_ROOT is not set. " +
        "Pass an absolute path to the extracted diagnosis bundle root.",
    );
  }
  if (!path.isAbsolute(root)) {
    throw new ToolInputError(`bundle_root must be an absolute path, got: ${root}`);
  }
  return root;
}
