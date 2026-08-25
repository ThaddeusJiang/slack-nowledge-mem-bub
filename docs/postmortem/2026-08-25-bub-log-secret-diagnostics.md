# Bub Exception Diagnostics Exposed Local Secrets

## What happened

A Bub Agent exception rendered stack-frame local variables in a redirected
gateway log. The local `AgentSettings` representation exposed a substantial
prefix of a configured model-provider API key.

## Root cause

Bub registered its stderr and optional Logfire sinks without overriding
Loguru's `diagnose=True` default. Any exception logged through those sinks could
therefore include local variable values, not only values held by
`AgentSettings`.

## Fix applied

The upstream report is tracked in `bubbuild/bub#292`. Pull request
`bubbuild/bub#293` explicitly sets `diagnose=False` on both Bub-owned sinks and
adds a regression test for that policy. The full upstream check and test suites
pass locally. The project friction remains linked until the upstream fix is
merged.

## What we learned

Exception-local diagnostics are a secret boundary. Redaction at one settings
type is incomplete because plugins and request handlers may hold other tokens;
the safe default must be enforced where the application registers log sinks.
