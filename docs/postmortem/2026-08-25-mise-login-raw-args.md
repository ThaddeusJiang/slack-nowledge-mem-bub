# Mise Login Task Rejected `raw_args`

## What happened

The provider login task added `raw_args = true` to `mise.toml`. The installed
mise version rejected that field while parsing the project configuration, so
every project task failed before it could run.

## Root cause

The task used a newer mise task field without verifying compatibility with the
mise version used by the deployment environment. The project pins Python and
`uv`, but it does not enforce a mise version that supports `raw_args`.

## Fix applied

The login task now declares one required `provider` argument through mise's
supported `usage` field and passes `$usage_provider` to `bub login`. This keeps
the documented `mise login openai` command while restoring configuration
parsing on the deployment environment.

## What we learned

New mise task fields must be validated by parsing the full project config in
the supported deployment environment. For thin task wrappers, prefer the
oldest supported declarative argument contract unless the project explicitly
enforces a newer mise version.
