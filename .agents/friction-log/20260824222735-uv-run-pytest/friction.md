---
title: 'uv run pytest fails after repository path changes'
severity: 'minor'
---

## Expected Behavior

`uv run pytest` runs after a checkout is moved or renamed.

## Current Behavior

It fails with `Failed to spawn: pytest` because `.venv/bin/pytest` keeps an absolute shebang to the previous checkout path.

## Possible Solution

Document that `uv sync --group dev` must be run after moving the checkout, or make the validation bootstrap refresh stale virtual environment entry points.

## Minimal Reproducible Example

1. Create the virtual environment with `uv sync`.
2. Move the checkout to another directory.
3. Run `uv run pytest`.

## Context

The stale shebang pointed to `/Users/amami/git/slack-nowledge-mem-bub/.venv/bin/python`, while the checkout is now under `/Users/amami/git/thaddeusjiang/slack-nowledge-mem-bub`.
