---
name: slack-nowledge-mem-bub-setup
description: Bootstrap, set up, validate, deploy, or operate the public slack-nowledge-mem-bub project and its dedicated Slack Socket Mode app. Use when the project may not be cloned yet, or for Slack manifest creation, scopes/events/token checks, environment configuration, deployment isolation, startup, and end-to-end acceptance. Do not use for ordinary Slack messaging or unrelated Slack apps.
---

# Slack Nowledge Mem Bub Setup

Bootstrap and operate one `slack-nowledge-mem-bub` instance for one Slack
workspace. This skill can be read before the project exists locally.

Canonical public resources:

- Project: <https://github.com/ThaddeusJiang/slack-nowledge-mem-bub>
- This skill: <https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/SKILL.md>

Automate non-secret setup where authorized, but keep installation, credentials,
and external writes inside explicit user-approved boundaries.

## Locate or acquire the project first

Read
[references/bootstrap.md](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/references/bootstrap.md)
before assuming a local checkout. Reuse the current directory only when its Git
remote matches the canonical project. Otherwise clone the public repository into
an explicit persistent target directory. Use the archive download only when Git
is unavailable.

After acquisition, read `AGENTS.md`, `README.md`,
`docs/specs/001-slack-team-memory.md`, `.env.example`, and `mise.toml` from that
checkout before acting. Treat those files and current code as authoritative when
they differ from this skill.

Do not modify the runtime Slack skill at `src/skills/slack/`: that skill handles
proactive messages after deployment and is not an installation guide.

## Route the task

- For repository discovery, clone, or download, read
  [references/bootstrap.md](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/references/bootstrap.md).
- For Slack App creation or verification, read
  [references/slack-app.md](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/references/slack-app.md).
  When creating an app, use
  [assets/slack-app-manifest.yaml](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/assets/slack-app-manifest.yaml).
- For environment configuration, deployment, startup, usage, or acceptance,
  read
  [references/runtime.md](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/references/runtime.md).
- For a complete setup or audit, read all three references and verify each layer
  in order: source, Slack App, secrets, Mem/model dependencies, gateway, then
  user flow.

## Hard boundaries

- Deploy one process per Slack workspace, with a dedicated Slack App and
  isolated Nowledge Mem credentials/data. The current configuration accepts one
  `xoxb-` token and one `xapp-` token, and Mem thread IDs omit Slack team ID.
- Do not enable public distribution or claim multi-workspace support. Sharing
  one app across workspaces requires OAuth installation, per-workspace token
  storage, `team_id` routing, and tenant-aware Mem isolation that this project
  does not implement.
- Never put Slack tokens, model API keys, or Mem API keys in chat, skill files,
  patches, commands, logs, screenshots, browser snapshots, or memory. Never
  print an existing `.env`. Let the user enter or copy secrets directly into
  the selected local secret file or deployment platform.
- Do not request a Slack Signing Secret. Socket Mode needs the App-Level Token
  with `connections:write` and the Bot User OAuth Token; this project does not
  use an HTTP Events API request URL.
- Do not overwrite an existing checkout, `.env`, or running deployment. Inspect
  key names without values, then create an isolated deployment/configuration
  when another Slack App is already in use.
- Confirm the target workspace and app name before the first Slack write. A
  setup request does not authorize deleting an app, revoking or rotating
  credentials, enabling distribution, or broadening requested scopes.

## Execution workflow

1. Locate a matching checkout or acquire the public project in an explicit
   persistent directory.
2. Inspect the repository, existing deployment state, and prior decisions.
3. Confirm the single-workspace target and whether the task is create, verify,
   run, or repair.
4. Configure or verify the Slack App against the exact manifest contract. Use
   authenticated browser automation only when necessary; keep token values out
   of snapshots and output.
5. Pause for the user to install/authorize the app and store the generated
   `xoxb-` and `xapp-` values securely. Resume by checking only that required
   token entries and scopes exist.
6. Prepare isolated runtime configuration from `.env.example`. Preserve
   `NMEM_SESSION_CONTEXT=0`, `NMEM_SESSION_DIGEST=0`, and `BUB_MAX_STEPS=4`.
7. Provision with `mise`, verify Nowledge Mem and Bub hooks, then start the
   gateway in the foreground before designing any service wrapper.
8. Validate from the user's perspective: passive capture, addressed reply,
   Slack thread continuity, acknowledgements, and Mem thread placement.

## Completion report

Report the source revision, Slack App configuration, deployment target,
commands run, observable validation, and remaining risks. Report only whether
each secret is configured; never include or partially reveal secret values.
