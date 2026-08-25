---
title: 'fix: prevent exception diagnostics from exposing local secrets'
severity: 'major'
target: 'bubbuild/bub'
issue: 'bubbuild/bub#292'
---

## What happened

Bub configures Loguru sinks with the default `diagnose=True`. When an exception is logged, Loguru can render stack-frame local variables. An Agent failure therefore exposed part of a configured provider API key through the `AgentSettings` representation in a redirected gateway log.

## Expected behavior

Bub-owned log sinks should preserve the traceback and error message without rendering local variable values.

## Reproduction

1. Configure Bub with a model-provider API key.
2. Run the gateway and trigger an Agent exception, such as exhausting a low `BUB_MAX_STEPS` limit.
3. Inspect the `Error processing inbound message` traceback.

## Proposed fix

Pass `diagnose=False` to every sink registered by `_instrument_bub()`. This disables local-variable diagnostics for both stderr and Logfire without changing exception propagation or ordinary logging.

A focused regression test can assert that every Bub-owned sink explicitly disables diagnostics.
