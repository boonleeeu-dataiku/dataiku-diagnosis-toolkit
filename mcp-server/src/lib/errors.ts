/** Expected, user-facing input problems. Handlers catch these and return an isError tool result
 * instead of letting them propagate as a raw exception. */
export class ToolInputError extends Error {}
