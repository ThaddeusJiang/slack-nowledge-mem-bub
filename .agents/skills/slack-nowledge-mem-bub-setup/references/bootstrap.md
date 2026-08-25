# Project Bootstrap

## Canonical source

The public source of truth is:

```text
https://github.com/ThaddeusJiang/slack-nowledge-mem-bub
```

Do not require the user to clone the project before invoking this skill. The
skill may be opened from its public raw URL, then acquire the project as part of
the workflow.

## Reuse a matching checkout

If the current directory is a Git repository, inspect its remote without
changing it:

```bash
git remote get-url origin
```

Normalize SSH and HTTPS GitHub forms when comparing the result. Reuse the
directory only when it resolves to
`ThaddeusJiang/slack-nowledge-mem-bub`. Do not treat an unrelated repository as
the target and do not rewrite its remote.

## Clone for deployment

Choose an explicit persistent target directory. Do not use a temporary
directory for a deployment that must keep running, and do not overwrite an
existing non-empty directory.

Prefer GitHub CLI when available:

```bash
gh repo clone ThaddeusJiang/slack-nowledge-mem-bub <target-directory>
```

Otherwise use Git directly:

```bash
git clone https://github.com/ThaddeusJiang/slack-nowledge-mem-bub.git <target-directory>
```

Record the checked-out commit with `git rev-parse HEAD` in the completion
report. Do not silently switch branches, discard local changes, or pull over a
dirty checkout.

## Download only when Git is unavailable

An archive is acceptable for a one-time installation, but it has no Git
history or safe update path. Confirm that `<target-directory>` does not exist,
then download the default branch archive:

```bash
bootstrap_tmp="$(mktemp -d)"
mkdir -p <target-directory>
curl -fsSL https://github.com/ThaddeusJiang/slack-nowledge-mem-bub/archive/refs/heads/main.tar.gz \
  -o "$bootstrap_tmp/source.tar.gz"
tar -xzf "$bootstrap_tmp/source.tar.gz" -C <target-directory> \
  --strip-components=1
```

Remove the temporary directory after a successful extraction. Never put
credentials in the archive URL, command line, or downloaded project tree.

## Verify the acquired source

Before configuration, confirm that these files exist in the target directory:

```text
AGENTS.md
README.md
.env.example
mise.toml
docs/specs/001-slack-team-memory.md
```

Read them locally and follow their current instructions. A public URL is enough
to start this skill, but an actual checkout or extracted source tree is required
to run the gateway.
