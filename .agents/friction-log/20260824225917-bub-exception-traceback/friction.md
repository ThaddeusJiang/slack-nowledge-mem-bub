---
title: 'Bub exception traceback exposes API key prefix from AgentSettings repr'
severity: 'major'
target: 'bubbuild/bub'
issue: 'bubbuild/bub#292'
---

## What happened

A `max_steps_reached` exception logged by Bub included the local `Agent` object and `AgentSettings` in Loguru traceback locals. The settings representation exposed a 28-character prefix of the configured model-provider API key in a world-readable `/tmp` gateway log.

## Expected

Exception diagnostics must redact secret settings such as `api_key` before rendering locals.

## Reproduction

1. Configure Bub with a model-provider API key.
2. Set a low `BUB_MAX_STEPS`.
3. Run `python -m bub gateway` and trigger a turn that exhausts the model loop.
4. Inspect the `Error processing inbound message` traceback.

## Environment

- Bub 0.4.2
- Python 3.14
- macOS

## Impact

Logs can disclose a substantial API-key prefix to other local users or log collectors.
