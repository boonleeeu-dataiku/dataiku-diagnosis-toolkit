import { promises as fs, createReadStream } from "node:fs";
import readline from "node:readline";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { resolveBundleRoot } from "../lib/bundle-root.js";
import { resolveWithinRoot } from "../lib/safe-path.js";
import { ToolInputError } from "../lib/errors.js";
import {
  BINARY_SNIFF_BYTES,
  DEFAULT_MAX_BYTES,
  DEFAULT_MAX_LINES,
  HARD_MAX_BYTES,
  HARD_MAX_LINES,
  SCAN_LINE_CAP,
} from "../lib/limits.js";

const inputShape = {
  bundle_root: z
    .string()
    .optional()
    .describe("Absolute bundle root; falls back to DATAIKU_BUNDLE_ROOT if omitted."),
  relative_path: z
    .string()
    .min(1)
    .describe(
      "Path to the target file, relative to bundle_root (e.g. 'datadir_listing.txt' or " +
        "'apps/dss/data_design/config/general-settings.json'). Must resolve inside bundle_root.",
    ),
  pattern: z
    .string()
    .optional()
    .describe("Optional JS-flavored regex; only matching lines are returned. Required for files above max_bytes."),
  pattern_flags: z.string().optional().describe("Optional regex flags, e.g. 'i'. Default none."),
  max_lines: z.number().int().positive().max(HARD_MAX_LINES).optional().default(DEFAULT_MAX_LINES),
  max_bytes: z.number().int().positive().max(HARD_MAX_BYTES).optional().default(DEFAULT_MAX_BYTES),
};

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  const units = ["K", "M", "G", "T"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)}${units[unit]}`;
}

async function looksBinary(absPath: string): Promise<boolean> {
  const fh = await fs.open(absPath, "r");
  try {
    const buf = Buffer.alloc(BINARY_SNIFF_BYTES);
    const { bytesRead } = await fh.read(buf, 0, BINARY_SNIFF_BYTES, 0);
    return buf.subarray(0, bytesRead).includes(0);
  } finally {
    await fh.close();
  }
}

function errorResult(text: string) {
  return { content: [{ type: "text" as const, text }], isError: true as const };
}

export function registerSafeReadTool(server: McpServer): void {
  server.registerTool(
    "safe_read",
    {
      title: "Guarded file read/grep within a bundle",
      description:
        "Read a bounded slice of a single file inside a diagnosis bundle, with hard size/line " +
        "caps and optional regex filtering. Use this instead of trying to load whole manifest/log " +
        "files - some (datadir_listing.txt, run/*.log.N, run/audit/audit.log.N) are 100MB-2.3GB. " +
        "See the reference-limitations and reference-listings-and-manifests resources for which " +
        "files need a pattern.",
      inputSchema: inputShape,
    },
    async ({ bundle_root, relative_path, pattern, pattern_flags, max_lines, max_bytes }) => {
      let bundleRoot: string;
      let absPath: string;
      try {
        bundleRoot = resolveBundleRoot(bundle_root);
        await fs.stat(bundleRoot).catch(() => {
          throw new ToolInputError(`bundle_root does not exist or is not accessible: ${bundleRoot}`);
        });
        absPath = await resolveWithinRoot(bundleRoot, relative_path);
      } catch (err) {
        if (err instanceof ToolInputError) return errorResult(err.message);
        throw err;
      }

      let stat;
      try {
        stat = await fs.stat(absPath);
      } catch (err) {
        const reason = err instanceof Error ? err.message : String(err);
        return errorResult(`Could not stat ${relative_path}: ${reason}`);
      }

      if (stat.isDirectory()) {
        let entryCount = "unknown";
        try {
          entryCount = String((await fs.readdir(absPath)).length);
        } catch {
          // best effort only
        }
        return errorResult(
          `relative_path is a directory, not a file: ${relative_path} (${entryCount} entries) - pass a file path.`,
        );
      }
      if (!stat.isFile()) {
        return errorResult(`relative_path is not a regular file: ${relative_path}`);
      }

      let regex: RegExp | undefined;
      if (pattern !== undefined) {
        try {
          regex = new RegExp(pattern, pattern_flags ?? "");
        } catch (err) {
          const reason = err instanceof Error ? err.message : String(err);
          return errorResult(`Invalid regex pattern: ${reason}`);
        }
      }

      if (!regex) {
        const binary = await looksBinary(absPath).catch(() => false);
        if (binary) {
          return errorResult(
            `${relative_path} appears to be a binary file; safe_read is for text logs/manifests/JSON - ` +
              "pass a pattern if you specifically need to grep binary-adjacent content.",
          );
        }
        if (stat.size > max_bytes) {
          return errorResult(
            `${relative_path} is ${humanSize(stat.size)}, which exceeds max_bytes (${humanSize(max_bytes)}). ` +
              "Provide a pattern to filter, raise max_bytes up to the hard cap of " +
              `${humanSize(HARD_MAX_BYTES)}, or target a smaller relative_path.`,
          );
        }

        const text = await fs.readFile(absPath, "utf8");
        const lines = text.split("\n");
        const truncated = lines.length > max_lines;
        const shown = lines.slice(0, max_lines);
        const header =
          `[safe_read] file=${relative_path} size=${humanSize(stat.size)} ` +
          `lines_returned=${shown.length} truncated=${truncated ? "true(hit max_lines)" : "false"}`;
        return { content: [{ type: "text" as const, text: `${header}\n---\n${shown.join("\n")}` }] };
      }

      // Pattern branch: stream regardless of file size, bounded by max_lines / SCAN_LINE_CAP so
      // memory use is O(max_lines), never O(file size).
      const matches: string[] = [];
      let linesScanned = 0;
      const state: { stopReason: "matches" | "scan_cap" | "eof" } = { stopReason: "eof" };

      await new Promise<void>((resolve, reject) => {
        const stream = createReadStream(absPath, { encoding: "utf8" });
        const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

        const stop = (reason: "matches" | "scan_cap") => {
          state.stopReason = reason;
          rl.close();
          stream.destroy();
        };

        rl.on("line", (line) => {
          linesScanned += 1;
          if (regex!.test(line)) {
            matches.push(`${linesScanned}: ${line}`);
            if (matches.length >= max_lines) {
              stop("matches");
              return;
            }
          }
          if (linesScanned >= SCAN_LINE_CAP) {
            stop("scan_cap");
          }
        });
        rl.on("close", () => resolve());
        stream.on("error", (err) => reject(err));
      });

      const truncatedText =
        state.stopReason === "matches"
          ? "true(hit max_lines)"
          : state.stopReason === "scan_cap"
            ? "true(hit scan cap before max_lines found)"
            : "false";
      const header =
        `[safe_read] file=${relative_path} size=${humanSize(stat.size)} pattern=/${pattern}/${pattern_flags ?? ""} ` +
        `lines_scanned=${linesScanned} matches_returned=${matches.length} truncated=${truncatedText}`;
      return { content: [{ type: "text" as const, text: `${header}\n---\n${matches.join("\n")}` }] };
    },
  );
}
