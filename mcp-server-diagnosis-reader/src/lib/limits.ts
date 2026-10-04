// run_orient execution limits: orient.sh is killed after the timeout, and its output is capped so a
// pathological bundle can't make the server buffer unbounded text.
export const ORIENT_TIMEOUT_MS = 120_000;
export const ORIENT_MAX_BUFFER_BYTES = 5 * 1024 * 1024;
