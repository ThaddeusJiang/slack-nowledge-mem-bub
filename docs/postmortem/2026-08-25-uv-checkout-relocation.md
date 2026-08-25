# Stale Pytest Entrypoint After Checkout Relocation

## What happened

After the repository moved to a different path, `uv run pytest` failed to spawn
the environment's pytest executable. Its shebang still referenced the previous
checkout's `.venv/bin/python` path.

## Root cause

Virtual environment console scripts contain absolute interpreter paths. The
failure was tied to a stale environment created before the checkout moved, not
to the project test suite or the supported `mise test` task.

## Fix applied

No repository workaround was added. With the pinned uv 0.12.3, a fresh
environment was created, the checkout was moved while retaining the old pytest
shebang, and `uv run pytest --collect-only -q` still collected all 76 tests.
The supported `mise test` task also runs dependency setup first and invokes
pytest through `python -m pytest`. The obsolete friction issues were closed.

## What we learned

Reproduce environment relocation failures with the currently pinned toolchain
before adding bootstrap logic. Prefer module invocation in project tasks so a
stale console-script shebang is not part of the validation path.
