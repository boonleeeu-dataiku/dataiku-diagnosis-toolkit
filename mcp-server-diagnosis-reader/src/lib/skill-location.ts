import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url)); // dist/lib
// dist/lib -> dist -> mcp-server-diagnosis-reader -> repo root -> dataiku-diagnosis-reader
const DEFAULT_SKILL_ROOT = path.resolve(here, "..", "..", "..", "dataiku-diagnosis-reader");

export const SKILL_ROOT = process.env.DATAIKU_SKILL_DIR
  ? path.resolve(process.env.DATAIKU_SKILL_DIR)
  : DEFAULT_SKILL_ROOT;
