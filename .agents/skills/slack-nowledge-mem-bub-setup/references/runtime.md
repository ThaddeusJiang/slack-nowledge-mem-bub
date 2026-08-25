# Runtime Setup and Use

## Deployment isolation

Use a separate process, source directory, and configuration for each Slack
workspace. Do not place credentials for two Slack Apps in one `.env`, and do not
start separate workspace processes with the same App-Level Token. Use isolated
Nowledge Mem credentials/data for external companies.

If the selected checkout already has `.env`, inspect only its key names and
treat it as an existing deployment until proven otherwise. Do not overwrite it.
Choose another persistent checkout or deployment directory for the new App.
Ask for the target host or platform before creating a service manager,
container, or Kubernetes configuration because the repository does not define
one.

## Environment contract

Start from the repository's `.env.example`. Required runtime values are:

```env
BUB_SLACK_BOT_TOKEN=xoxb-...
BUB_SLACK_APP_TOKEN=xapp-...
NMEM_SESSION_CONTEXT=0
NMEM_SESSION_DIGEST=0
BUB_MAX_STEPS=4
```

Also configure the model provider required by Bub, for example
`OPENAI_API_KEY`. A remote Mem service additionally requires:

```env
NMEM_API_URL=https://your-nowledge-mem-server
NMEM_API_KEY=...
```

Optional access restrictions use Slack IDs:

```env
BUB_SLACK_ALLOW_CHANNELS=C123,C456
BUB_SLACK_ALLOW_USERS=U123,U456
```

The channel list restricts shared channels only. The user list applies to both
shared channels and DMs.

Never echo these values, embed them in a command line, or commit the secret
file. When checking configuration, report only present/missing key names.

## Provision and inspect

Use the project's pinned toolchain from the acquired source directory:

```bash
mise trust
mise install
mise setup
mise exec -- uv run nmem status
mise hooks
```

`mise hooks` must show `slack` under `provide_channels` and `nowledge_mem` under
the memory-related hooks. If the model is not configured, run:

```bash
mise exec -- uv run python -m bub onboard
```

## Start

Start the gateway in the foreground first:

```bash
mise dev
```

Socket Mode requires no public HTTP endpoint. Do not design a daemon, Docker,
systemd, launchd, or Kubernetes wrapper until the foreground gateway connects
and the user flow passes. For a later readiness probe, set `BUB_HEALTH_FILE` to
a writable path; the gateway creates it after connecting and removes it during
shutdown.

## User acceptance

Invite the bot to a test channel, then verify these observable contracts:

1. Post an ordinary non-empty human message without mentioning the bot. It is
   captured to `slack:{channel_id}` with no Agent run, reply, or acknowledgement.
2. Mention the bot in a shared channel or thread. The message receives
   `:hourglass:`, the Agent replies in the correct thread, then the reaction is
   replaced by `:white_check_mark:`.
3. Send the bot a DM. It replies using the channel-scoped session.
4. Continue in a Slack thread the bot joined. Plain follow-ups route to the
   Agent until the process restarts.
5. Inspect capture without exposing secrets:

   ```bash
   mise exec -- uv run nmem t show slack:{channel_id}
   mise exec -- uv run nmem t show slack:{channel_id}:{thread_ts}
   ```

Different Slack threads must remain isolated. After restart, explicitly mention
the bot once to reactivate an existing shared-channel thread.

## Current non-goals

Do not promise historical import, edit/delete synchronization, file or
attachment capture, persistent active-thread state, a retry queue, or
multi-workspace OAuth routing. Those are outside the current project contract.
