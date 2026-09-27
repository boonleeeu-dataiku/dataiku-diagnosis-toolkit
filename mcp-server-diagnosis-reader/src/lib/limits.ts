// safe_read hard ceilings. These are enforced both by the zod input schema (a caller cannot
// request a number above these) and, redundantly, as constants the handler itself is written
// against — see references/limitations.md for why this matters (bundle files observed at
// 100MB-2.3GB that must never be loaded whole).
export const HARD_MAX_BYTES = 5_000_000;
export const HARD_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 500_000;
export const DEFAULT_MAX_LINES = 500;

// Safety valve on a pattern scan: stop walking the file after this many lines even if max_lines
// hasn't been reached yet, so a non-matching pattern against a multi-GB file can't run forever.
export const SCAN_LINE_CAP = 5_000_000;

// Bytes sniffed from the start of a file to decide whether it looks binary.
export const BINARY_SNIFF_BYTES = 4096;

export const ORIENT_TIMEOUT_MS = 120_000;
export const ORIENT_MAX_BUFFER_BYTES = 5 * 1024 * 1024;
