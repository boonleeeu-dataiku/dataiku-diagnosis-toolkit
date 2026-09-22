import path from "node:path";
import { promises as fs } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SKILL_ROOT } from "../lib/skill-location.js";
import { resolveBundleRoot } from "../lib/bundle-root.js";
import { ToolInputError } from "../lib/errors.js";
import { ORIENT_MAX_BUFFER_BYTES, ORIENT_TIMEOUT_MS } from "../lib/limits.js";

const execFileAsync = promisify(execFile);

const inputShape = {
  bundle_root: z
    .string()
    .optional()
    .describe(
      "Absolute path to the bundle root (the directory containing diag.txt/timings.txt). " +
        "Falls back to the DATAIKU_BUNDLE_ROOT env var if omitted.",
    ),
};

export function registerRunOrientTool(server: McpServer): void {
  server.registerTool(
    "run_orient",
    {
      title: "Run orient.sh triage",
      description:
        "Runs the dataiku-diagnosis-reader skill's orient.sh triage script against bundle_root: " +
        "reports node type/version, the data-dir mirror location, the 10 largest files in the " +
        "bundle, and presence/size of key troubleshooting files (dmesg.txt, stacks.txt, " +
        "cgroups_usage.txt, run/sanity-check.json, hs_err_pid* crash dumps, run/audit/). " +
        "Read-only, no network calls, no changes made. Read the skill-guide resource first to " +
        "know how to interpret the output.",
      inputSchema: inputShape,
    },
    async ({ bundle_root }) => {
      let bundleRoot: string;
      try {
        bundleRoot = resolveBundleRoot(bundle_root);
      } catch (err) {
        if (err instanceof ToolInputError) {
          return { content: [{ type: "text" as const, text: err.message }], isError: true };
        }
        throw err;
      }

      const orientScript = path.join(SKILL_ROOT, "scripts", "orient.sh");
      try {
        await fs.access(orientScript);
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text:
                `Could not find orient.sh at ${orientScript}. Is dataiku-diagnosis-reader/ ` +
                "present as a sibling of mcp-server/, or is DATAIKU_SKILL_DIR set correctly?",
            },
          ],
          isError: true,
        };
      }

      try {
        // execFile with an argv array (never a shell string) means bundleRoot is passed as one
        // literal argument and cannot be shell-interpreted, regardless of its content.
        const { stdout } = await execFileAsync("bash", [orientScript, bundleRoot], {
          timeout: ORIENT_TIMEOUT_MS,
          maxBuffer: ORIENT_MAX_BUFFER_BYTES,
        });
        return { content: [{ type: "text" as const, text: stdout }] };
      } catch (err: unknown) {
        const e = err as { stdout?: string; stderr?: string; message?: string; killed?: boolean; signal?: string };
        if (e.stdout !== undefined || e.stderr !== undefined) {
          const text = [e.stdout, e.stderr ? `--- stderr ---\n${e.stderr}` : undefined]
            .filter(Boolean)
            .join("\n");
          return { content: [{ type: "text" as const, text: text || (e.message ?? "orient.sh failed") }], isError: true };
        }
        return {
          content: [
            {
              type: "text" as const,
              text: `Failed to run orient.sh: ${e.message ?? String(err)}`,
            },
          ],
          isError: true,
        };
      }
    },
  );
}
