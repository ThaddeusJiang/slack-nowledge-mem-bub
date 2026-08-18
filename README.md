# slack-nowledge-mem-bub

> This project derives from `bub-slack` in `bubbuild/bub-contrib` and modifies it for passive Nowledge Mem capture.

Slack Team Memory for [Bub](https://github.com/bubbuild/bub) and [Nowledge Mem](https://mem.nowledge.co/).

The project gives Slack two paths:

```text
Ordinary message -> Nowledge Mem
Message to @Bot  -> Nowledge Mem -> Bub Agent -> Slack
```

Team messages are captured without calling an LLM. The Agent runs only for direct messages, explicit mentions, and follow-ups in a thread it has joined.

## Requirements

- Python 3.12+
- A Slack app with Socket Mode enabled
- A running Nowledge Mem service
- A model provider supported by Bub

## Setup

Clone the project and install its dependencies:

```bash
git clone https://github.com/ThaddeusJiang/slack-nowledge-mem-bub.git
cd slack-nowledge-mem-bub
uv sync
```

Confirm that Nowledge Mem is available:

```bash
uv run nmem status
```

Copy the environment template:

```bash
cp .env.example .env
```

Set both Slack tokens and the API key required by your Bub model provider. For example:

```env
BUB_SLACK_BOT_TOKEN=xoxb-...
BUB_SLACK_APP_TOKEN=xapp-...
OPENAI_API_KEY=...
```

The local Nowledge Mem API defaults to `http://127.0.0.1:14242`. For a remote service, also set:

```env
NMEM_API_URL=https://your-nowledge-mem-server
NMEM_API_KEY=...
```

Keep these values disabled:

```env
NMEM_SESSION_CONTEXT=0
NMEM_SESSION_DIGEST=0
```

Slack messages are already captured directly. Disabling the session digest prevents `nowledge-mem-bub` from creating a second `source=bub` thread for the same conversation.

Run Bub onboarding if the model or other Bub settings are not configured yet:

```bash
uv run bub onboard
```

## Slack app

### Socket Mode

Enable Socket Mode and create an app-level token with:

```text
connections:write
```

Use that token as `BUB_SLACK_APP_TOKEN`.

### Bot scopes

Add these Bot Token Scopes:

```text
chat:write
channels:history
groups:history
im:history
reactions:write
users:read
```

- History scopes receive messages and fetch Slack thread roots.
- `users:read` resolves `<@USER_ID>` mentions to display names.
- `reactions:write` provides the processing acknowledgement.

Use the Bot User OAuth Token as `BUB_SLACK_BOT_TOKEN`.

### Event subscriptions

Subscribe to:

```text
message.channels
message.groups
message.im
```

Invite the bot to every shared channel it should capture.

## Run

Check that both plugins are loaded:

```bash
uv run bub hooks
```

The output should include `slack` under `provide_channels` and `nowledge_mem` under the memory-related hooks.

Start the Slack gateway:

```bash
uv run bub gateway
```

No public HTTP endpoint is required. Slack events arrive through Socket Mode.

For a process or Kubernetes readiness probe, set `BUB_HEALTH_FILE` to a writable path. The gateway creates the file after Socket Mode connects and removes it on shutdown.

## Use

### Capture team messages

Post an ordinary message in a channel where the bot is present. The message is saved to Nowledge Mem without an Agent turn or Slack reply.

Top-level messages are stored in:

```text
slack:{channel_id}
```

Slack replies are stored in a dedicated thread:

```text
slack:{channel_id}:{thread_ts}
```

Inspect either thread with:

```bash
uv run nmem t show slack:{channel_id}
uv run nmem t show slack:{channel_id}:{thread_ts}
```

### Ask the Agent

- Mention the bot in a shared channel or Slack thread.
- Send any direct message to the bot.
- After the bot replies in a Slack thread, continue replying there without mentioning it again.

An addressed message receives `:hourglass:` while it is being processed and `:white_check_mark:` after the first response.

### Restrict access

Use comma-separated Slack IDs:

```env
BUB_SLACK_ALLOW_CHANNELS=C123,C456
BUB_SLACK_ALLOW_USERS=U123,U456
```

Both lists apply to passive capture and Agent turns. The channel list restricts shared channels only; direct messages are restricted by the user list.

## Behavior notes

- Slack user mentions are stored as current display names when `users.info` succeeds.
- Message metadata includes Slack channel, thread, user, timestamp, and permalink information.
- Capture and enrichment are best-effort. A Nowledge Mem or Slack metadata failure does not block an addressed Agent turn.
- The set of Slack threads joined by the bot is stored in process memory. After a gateway restart, mention the bot once to reactivate an existing thread.
- Rapid messages may be debounced into one Agent turn, while each accepted Slack event is still captured separately.
- Long Agent responses are split into Slack-safe chunks.
- The project does not import history or synchronize edits, deletions, files, or attachments.

See [`docs/specs/001-slack-team-memory.md`](docs/specs/001-slack-team-memory.md) for the behavior contract.

## Acknowledgements

This project is a focused fork of [`bub-slack`](https://github.com/bubbuild/bub-contrib/tree/main/packages/bub-slack) and reuses [Bub](https://github.com/bubbuild/bub) and [`nowledge-mem-bub`](https://github.com/nowledge-co/community/tree/main/nowledge-mem-bub-plugin).

## Author

Maintained by [Thaddeus Jiang](https://github.com/ThaddeusJiang).

## License

[Apache License 2.0](LICENSE)
