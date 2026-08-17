# Agent Guidelines

## Project

`slack-nowledge-mem-bub` is a Bub channel plugin that gives Slack two independent paths:

1. accepted human messages are passively appended to Nowledge Mem;
2. addressed messages also enter the Bub Agent and receive an automatic Slack reply.

Keep the project focused on validating this Slack Team Memory workflow. Do not introduce a generic connector framework, queue, retry system, or new Bub abstraction without a concrete requirement.

## Documentation

- Write all project documentation, code comments, docstrings, tests, and user-facing text in English.
- Keep documentation concise and aligned with verified code behavior.
- Use `README.md` for installation and usage.
- Use `AGENTS.md` for architecture, maintenance constraints, and validation.
- Use `docs/specs/` for durable feature behavior and acceptance criteria.
- Name specs `NNN-feature-name.md`. Keep one spec per cohesive feature; do not split a small feature only to create more files.
- Update the relevant spec whenever a behavior contract changes.

## Architecture

The package is a minimal fork of `bub-slack`. It extends the existing Slack message path without modifying Bub Core or `nowledge-mem-bub`.

Key files:

| Path | Responsibility |
| --- | --- |
| `src/bub_slack/plugin.py` | Bub hooks, Slack channel registration, and the automatic-response prompt contract |
| `src/bub_slack/config.py` | `BUB_SLACK_*` settings registered with Bub |
| `src/bub_slack/channel.py` | Socket Mode lifecycle, event filtering, Agent routing, Slack replies, reactions, and mention resolution |
| `src/bub_slack/nowledge.py` | Best-effort Mem thread creation and message append logic |
| `src/skills/slack/` | Proactive Slack send, edit, and reaction skill exposed to the Agent |
| `tests/` | Executable behavior contracts |
| `docs/specs/001-slack-team-memory.md` | Product-level Slack Team Memory contract |

Runtime flow:

```text
Slack message
-> filter event and apply allow-lists
-> resolve user mentions
-> capture in Nowledge Mem
-> stop if not addressed
-> Bub Agent
-> automatic Slack reply
-> capture the assistant reply
```

## Behavior invariants

Preserve these rules unless the feature specification is intentionally changed.

### Channel lifecycle

- Enable the channel only when both Slack tokens are present.
- Construct the Socket Mode client inside the running event loop.
- `start()` must connect and return. Never wait on `stop_event`; Bub starts channels sequentially before its consumer loop.
- When `BUB_HEALTH_FILE` is set, create it after Socket Mode connects and remove it during shutdown.
- Keep debounce enabled for rapid Agent-bound messages. Passive capture still runs once per accepted Slack event.

### Event acceptance

- Ignore Slack message subtypes, bot messages, and self echoes before capture.
- Apply the same user and channel policy to passive capture and Agent turns.
- `BUB_SLACK_ALLOW_CHANNELS` restricts shared channels, not DMs.
- `BUB_SLACK_ALLOW_USERS` restricts both shared channels and DMs.
- Resolve `<@USER_ID>` tokens through `users.info`; retain the original token on failure.

### Agent routing

- Every accepted non-empty human message is captured before the addressed-message decision.
- DMs are always addressed.
- Shared-channel messages require an explicit bot mention unless they are replies in a thread the bot has joined.
- Active Slack threads are process-local state and reset on restart.
- DM sessions are channel-scoped: `slack:{channel_id}`.
- Shared-channel Agent sessions are thread-scoped: `slack:{channel_id}:{thread_root_ts}`.
- Distinct top-level mentions must not share Agent session state.

### Memory mapping

- Top-level Slack messages append to `slack:{channel_id}`.
- Slack replies append to `slack:{channel_id}:{thread_ts}`.
- When a dedicated Slack thread is first created, fetch its root and create it with `[root, first reply]` when possible.
- User and assistant replies in one Slack thread must share one Mem thread.
- Different Slack threads must remain isolated.
- Use Slack `ts` in the idempotency key.
- Preserve Slack provenance in message and thread metadata.
- Capture assistant messages directly after posting; continue ignoring echoed bot events to prevent duplicates.

### Failure boundaries

- Passive capture, permalink lookup, root enrichment, mention enrichment, and reactions are best-effort.
- A Mem or enrichment failure must not prevent an addressed message from reaching the Agent.
- A capture failure must not break Slack event handling or outbound delivery.
- Keep connect timeouts short enough to fail promptly while allowing committed Mem writes to complete.

### Slack replies

- Bub Router automatically posts the final response to Slack.
- Never use `slack_send.py` for the ordinary response to the current turn; doing so creates a duplicate.
- Use the Slack skill only for proactive cross-target messages, edits, or out-of-band reactions.
- Recover `thread_ts` from the thread-scoped session ID when Bub drops inbound context.
- Keep outbound chunks below Slack's 4,000-character limit.
- Add `:hourglass:` when accepting an addressed message and replace it with `:white_check_mark:` after the first reply. Reaction failures remain non-fatal.

## Change workflow

1. Read the relevant source, tests, and feature spec before changing behavior.
2. State the exact behavior and acceptance criteria being changed.
3. Make the smallest implementation change that satisfies the requirement.
4. Add or update focused tests for the changed contract.
5. Update README only when setup or user workflow changes.
6. Update the feature spec when externally observable behavior changes.
7. Run the validation commands before finishing.

Do not refactor adjacent code or modify upstream Bub components unless the task requires it. Prefer explicit code in the existing message path over a new abstraction for a single use case.

## Validation

Run:

```bash
uv run pytest -q
uv build
git diff --check
```

For documentation changes, also confirm that project-authored text contains no CJK characters:

```bash
rg -n --glob '!{.git,.venv,.pytest_cache,.ruff_cache,dist}/**' '[\p{Han}\p{Hiragana}\p{Katakana}\p{Hangul}]' .
```

Relevant test ownership:

| Area | Tests |
| --- | --- |
| Event filters, allow-lists, routing, sessions | `tests/test_channel_handle_message.py` |
| Socket Mode lifecycle and readiness | `tests/test_channel_lifecycle.py` |
| Acknowledgement reactions | `tests/test_channel_ack.py` |
| Reply routing, chunking, assistant capture | `tests/test_channel_send.py` |
| Mem mapping, metadata, idempotency, fallback creation | `tests/test_nowledge.py` |
| Settings and plugin registration | `tests/test_config.py`, `tests/test_plugin_discovery.py` |

## Friction Logging

- If `frog` is not installed, install it with `curl -fsSL https://frog.fm/install | sh`.
- Run `frog list` before starting work.
- Log project or dependency papercuts with `frog log` as they are encountered.
- Do not log global, system, or internal friction.
