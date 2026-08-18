---
title: 'uv build warns that installed uv is outside the declared uv-build range'
severity: 'minor'
issue: 'ThaddeusJiang/slack-nowledge-mem-bub#1'
---

## Expected Behavior

`uv build` completes without a build-system version warning.

## Current Behavior

With uv 0.12.3, `uv build` warns that `build_system.requires = ["uv-build>=0.10.4,<0.11.0"]` does not contain the current uv version. The source distribution and wheel still build successfully.

## Possible Solution

Verify compatibility with uv-build 0.12 and update the declared range, or document the expected uv version.

## Minimal Reproducible Example

```bash
uv --version
uv build
```

## Context

Observed while validating an English-only documentation update. It does not block the build, but makes it unclear whether the local build toolchain is supported.
