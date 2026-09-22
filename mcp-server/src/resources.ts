import path from "node:path";
import { promises as fs } from "node:fs";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SKILL_ROOT } from "./lib/skill-location.js";

interface ResourceDef {
  file: string;
  uri: string;
  name: string;
  title: string;
}

// SKILL.md + all 8 references/*.md files. This list must stay in sync with what actually ships
// under dataiku-diagnosis-reader/ — there is deliberately no directory scan here, so a new
// reference file added to the skill needs a corresponding entry added here too.
const RESOURCE_FILES: ResourceDef[] = [
  {
    file: "SKILL.md",
    uri: "dataiku-skill://SKILL.md",
    name: "skill-guide",
    title: "SKILL.md — Dataiku diagnosis.zip reader overview",
  },
  {
    file: "references/root-files.md",
    uri: "dataiku-skill://references/root-files.md",
    name: "reference-root-files",
    title: "Root .txt files deep dive",
  },
  {
    file: "references/lookup-table.md",
    uri: "dataiku-skill://references/lookup-table.md",
    name: "reference-lookup-table",
    title: "Full 'where do I find X' lookup table",
  },
  {
    file: "references/data-dir-config.md",
    uri: "dataiku-skill://references/data-dir-config.md",
    name: "reference-data-dir-config",
    title: "config/ metastore reference",
  },
  {
    file: "references/data-dir-runtime-and-codeenvs.md",
    uri: "dataiku-skill://references/data-dir-runtime-and-codeenvs.md",
    name: "reference-data-dir-runtime-and-codeenvs",
    title: "run/ logs, code-envs/, plugins/dev/",
  },
  {
    file: "references/limitations.md",
    uri: "dataiku-skill://references/limitations.md",
    name: "reference-limitations",
    title: "Verified scope, content gaps, large-file hazards",
  },
  {
    file: "references/node-types.md",
    uri: "dataiku-skill://references/node-types.md",
    name: "reference-node-types",
    title: "design vs automation node differences",
  },
  {
    file: "references/data-dir-identity.md",
    uri: "dataiku-skill://references/data-dir-identity.md",
    name: "reference-data-dir-identity",
    title: "Finding the data-dir mirror, install.ini, dss-version.json",
  },
  {
    file: "references/listings-and-manifests.md",
    uri: "dataiku-skill://references/listings-and-manifests.md",
    name: "reference-listings-and-manifests",
    title: "Safely querying find -ls manifest files",
  },
];

export function registerResources(server: McpServer): void {
  for (const r of RESOURCE_FILES) {
    server.registerResource(r.name, r.uri, { title: r.title, mimeType: "text/markdown" }, async (uri) => {
      const abs = path.join(SKILL_ROOT, r.file);
      let text: string;
      try {
        text = await fs.readFile(abs, "utf8");
      } catch (err) {
        const reason = err instanceof Error ? err.message : String(err);
        throw new Error(
          `Could not read ${r.file} at ${abs} (${reason}). Is dataiku-diagnosis-reader/ present ` +
            "as a sibling of mcp-server/, or is DATAIKU_SKILL_DIR set correctly?",
        );
      }
      return { contents: [{ uri: uri.href, mimeType: "text/markdown", text }] };
    });
  }
}
