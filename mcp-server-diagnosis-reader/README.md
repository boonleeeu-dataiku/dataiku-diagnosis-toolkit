# dataiku-diagnosis-reader-mcp

A thin local [MCP](https://modelcontextprotocol.io) server that exposes the `dataiku-diagnosis-reader`
Claude Code Skill to MCP-compatible agents that can't load Claude Code skills directly — Cursor,
Claude Desktop, and similar tools.

**This server contains no diagnostic logic of its own.** `../dataiku-diagnosis-reader/` is the
single source of truth: `SKILL.md` and `references/*.md` are read from disk at request time (not
copied or embedded), and `scripts/orient.sh` is invoked as a subprocess. Editing the skill package
takes effect immediately for anyone using this server — no rebuild needed unless you also change
this server's own TypeScript code.

## Requirements

- Node.js >= 18.17
- `bash` on `PATH` (same requirement as `orient.sh` itself — macOS/Linux native; Windows users need
  WSL or Git Bash)

## Build

```sh
cd mcp-server-diagnosis-reader
npm install
npm run build
```

This produces `dist/index.js`, the server's stdio entrypoint.

## What it exposes

### Resources (static skill content, read fresh from disk on every request)

| URI | Contents |
|---|---|
| `dataiku-skill://SKILL.md` | Skill overview: 3-tier content model, investigation workflow, quick-lookup table |
| `dataiku-skill://references/root-files.md` | Root `.txt` files deep dive |
| `dataiku-skill://references/lookup-table.md` | Full "where do I find X" lookup table |
| `dataiku-skill://references/data-dir-config.md` | `config/` metastore reference |
| `dataiku-skill://references/data-dir-runtime-and-codeenvs.md` | `run/` logs, `code-envs/`, `plugins/dev/` |
| `dataiku-skill://references/limitations.md` | Verified scope, content gaps, large-file hazards |
| `dataiku-skill://references/node-types.md` | design vs automation node differences |
| `dataiku-skill://references/data-dir-identity.md` | Finding the data-dir mirror, `install.ini`, `dss-version.json` |
| `dataiku-skill://references/listings-and-manifests.md` | Safely querying `find -ls` manifest files |

A calling agent should read `dataiku-skill://SKILL.md` first, then the relevant reference(s), to
figure out routing — the same way an agent using the skill directly would.

### Tools

#### `run_orient`

Runs `orient.sh` against a bundle: reports node type/version, the data-dir mirror location, the 10
largest files in the bundle, and presence/size of key troubleshooting files. Read-only, no network
calls.

| Param | Type | Required | Notes |
|---|---|---|---|
| `bundle_root` | string | no | Absolute path to the bundle root. Falls back to `DATAIKU_BUNDLE_ROOT` env var. |

Example call:

```json
{ "name": "run_orient", "arguments": { "bundle_root": "/Users/me/Downloads/dku_diagnosis_2026-01-01" } }
```

The server deliberately has no file-reading tool. After `run_orient`, the calling agent reads
bundle files with its own read/search tools, following the size and safety guidance in the
`limitations` and `listings-and-manifests` resources (some files are 100MB-2.3GB and must be
grepped, never loaded whole). A guarded `safe_read` tool existed up to 0.2.x and was removed in
0.3.0 because agents never used it; see `CHANGELOG.md`.

### Environment variables

- `DATAIKU_BUNDLE_ROOT` — default `bundle_root` for `run_orient` when the caller omits it.
- `DATAIKU_SKILL_DIR` — override for locating `dataiku-diagnosis-reader/`. Defaults to the sibling
  directory of this package (`../dataiku-diagnosis-reader` relative to
  `mcp-server-diagnosis-reader/`).

## Client configuration

The repo path may contain spaces — that's fine inside a JSON array element, just don't inline it
unquoted into a shell command elsewhere.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "dataiku-diagnosis-reader": {
      "command": "node",
      "args": ["/absolute/path/to/Diagnosis Reader/mcp-server-diagnosis-reader/dist/index.js"]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`, or Settings > MCP)

```json
{
  "mcpServers": {
    "dataiku-diagnosis-reader": {
      "command": "node",
      "args": ["/absolute/path/to/Diagnosis Reader/mcp-server-diagnosis-reader/dist/index.js"]
    }
  }
}
```

To set a default bundle so callers don't need to pass `bundle_root` every time, add an `env` block:

```json
{
  "mcpServers": {
    "dataiku-diagnosis-reader": {
      "command": "node",
      "args": ["/absolute/path/to/Diagnosis Reader/mcp-server-diagnosis-reader/dist/index.js"],
      "env": { "DATAIKU_BUNDLE_ROOT": "/absolute/path/to/some/dku_diagnosis_bundle" }
    }
  }
}
```

## Security / privacy

This server only ever touches paths explicitly passed as `bundle_root`/`relative_path` by the
calling agent. It ships no bundle data of its own. It must never be pointed at, or made to
reference, this repo's own `resources/` directory — that directory holds real, private diagnosis
bundles used only for local development/verification, is gitignored, and is never distributed.

## Testing

```sh
npm test
```

This builds, then runs the `node:test` suites in `test/` and `scripts/smoke-test.mjs`, all over real
stdio JSON-RPC against `dist/`, with no extra dependencies. The suites cover:
- `run_orient` output on design and automation bundles
- that the resource list stays in sync with `references/*.md`

The fixtures in `test/fixtures/bundles/` are hand-written synthetic bundles (see
`test/fixtures/README.md`). Edge cases that need a throwaway bundle are built in a temp directory at test time.

For interactive exploration, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```sh
npx @modelcontextprotocol/inspector node dist/index.js
```

This opens a local web UI to list and call resources/tools interactively — point
`run_orient` at a real bundle under `../resources/` for local verification (never reference a
specific bundle name in committed docs or tests).

## Troubleshooting

- **Server exits immediately / client shows a JSON parse error**: something wrote to stdout
  besides the SDK itself (e.g. a stray `console.log`). Check `src/**` and any dependency for
  non-stderr output.
- **"Could not find SKILL.md" / "Could not find orient.sh"**: `dataiku-diagnosis-reader/` isn't
  present as a sibling of `mcp-server-diagnosis-reader/`, or `DATAIKU_SKILL_DIR` is set incorrectly.
