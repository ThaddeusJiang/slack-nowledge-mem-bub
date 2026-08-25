---
title: 'mise login task uses unsupported raw_args field'
severity: 'major'
issue: 'ThaddeusJiang/slack-nowledge-mem-bub#12'
---

## Expected Behavior

The documented `mise login openai` command parses and forwards the provider argument on the supported deployment environment.

## Current Behavior

The project configuration fails to parse, so every mise task is blocked before execution. The deployed mise version rejects `raw_args` in `mise.toml` as an unknown task field.

## Possible Solution

Replace `raw_args` with a declarative required `provider` usage argument and pass `$usage_provider` to Bub.

## Minimal Reproducible Example

Run `mise tasks` with the affected `mise.toml`; parsing stops at `raw_args = true`.

## Context

The issue was discovered during deployment preflight immediately after the provider login task was merged.
