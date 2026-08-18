---
title: 'Package version differs between pyproject.toml and bub_slack.__version__'
severity: 'minor'
issue: 'ThaddeusJiang/slack-nowledge-mem-bub#2'
---

## Expected Behavior

The package version has one synchronized value across package metadata and runtime exports.

## Current Behavior

`pyproject.toml` declares version `0.1.4`, while `src/bub_slack/__init__.py` exports `__version__ = "0.1.0"`.

## Possible Solution

Use generated package metadata as the single source of truth, or update `__version__` as part of each release.

## Minimal Reproducible Example

```bash
rg -n "version|__version__" pyproject.toml src/bub_slack/__init__.py
```

## Context

Found while reviewing the current implementation before restructuring project documentation. This documentation task does not require changing runtime code.
