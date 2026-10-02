---
type: llm
---

PASS if the reply says this is a design node, and attributes the crash to memory exhaustion
(for example the JVM running out of native memory per the hs_err_pid crash dump, and/or the
kernel OOM-killer killing java per dmesg).
FAIL if it names a different node type, gives no cause, or attributes the crash to something
unrelated to memory.
