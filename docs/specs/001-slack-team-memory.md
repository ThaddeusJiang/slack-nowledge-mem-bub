# Slack Team Memory

## Purpose

Capture Slack team conversations in Nowledge Mem without running an LLM for every message, while preserving Bub's Agent workflow for messages intentionally addressed to the bot.

```text
Ordinary accepted message -> Nowledge Mem
Addressed message         -> Nowledge Mem -> Bub Agent -> Slack reply
```

## Scope

The feature covers:

- Slack Socket Mode message ingestion;
- passive capture of accepted human messages;
- direct-message, mention, and active-thread Agent routing;
- channel and Slack thread mapping to Mem threads;
- automatic Slack replies and assistant-message capture;
- best-effort mention, permalink, root-message, and reaction enrichment;
- optional channel and user allow-lists.

It reuses Bub for Agent execution and `nowledge-mem-bub` for Agent memory tools. It does not change Bub Core.

## Gateway lifecycle

The Slack channel is enabled only when both the bot token and app token are configured.

Starting the channel must connect Socket Mode and return without blocking Bub's channel startup sequence. Stopping it closes the Socket Mode client.

When `BUB_HEALTH_FILE` is configured, the channel creates the marker after Socket Mode connects and removes it during shutdown. Marker write failures are logged and do not prevent startup.

The channel requests Bub debounce handling for rapid Agent-bound messages. Passive capture still runs for each accepted Slack event before Bub can coalesce Agent turns.

## Message acceptance

A Slack event is accepted only when all applicable conditions pass:

1. the event is a normal message without a subtype;
2. it is not from a bot or the current bot user;
3. shared-channel access is allowed by `BUB_SLACK_ALLOW_CHANNELS`, when configured;
4. user access is allowed by `BUB_SLACK_ALLOW_USERS`, when configured.

Capture additionally requires a channel ID, message timestamp, and non-empty content. An Agent turn requires non-empty content after the bot mention is removed.

The channel allow-list does not reject DMs. The user allow-list applies everywhere.

Accepted Slack `<@USER_ID>` tokens are resolved to current display names through `users.info`. Resolution is cached for the process. The original token is retained when enrichment fails.

## Passive capture

Every accepted human message is sent to Nowledge Mem before deciding whether to invoke the Agent.

Passive capture must not:

- call the LLM;
- produce a Slack reply;
- block an addressed Agent turn when Mem is unavailable;
- raise an error into the Socket Mode listener.

Bot messages echoed through Socket Mode are ignored. Automatic Bub replies are captured directly after Slack accepts them, preventing duplicate ingestion.

## Agent routing

An accepted message is addressed when at least one condition is true:

- the message is a DM;
- the message explicitly mentions the bot;
- the message is a reply in a Slack thread the bot has joined during the current process lifetime.

A shared-channel message that is not addressed is captured and then dropped from the Agent path.

The active-thread set is in-memory state. After a gateway restart, an existing Slack thread requires one new explicit mention before plain follow-up replies enter the Agent again.

### Agent session IDs

| Context | Session ID |
| --- | --- |
| DM | `slack:{channel_id}` |
| Shared-channel Slack reply | `slack:{channel_id}:{thread_ts}` |
| Top-level shared-channel mention | `slack:{channel_id}:{message_ts}` |

DMs keep continuous channel-scoped Agent state. Shared-channel threads and separate top-level mentions remain isolated.

## Memory model

### Channel thread

Top-level Slack messages append to:

```text
slack:{channel_id}
```

The Mem thread uses:

```json
{
  "source": "slack",
  "metadata": {
    "slack_channel_id": "C123"
  }
}
```

### Slack thread

Slack replies append to:

```text
slack:{channel_id}:{thread_ts}
```

For a Slack reply, the integration attempts to fetch the root through `conversations.replies` so it is available if the Mem thread must be created. If append reports that the thread does not exist and the root is available, the thread is created with:

```text
[root message, first captured reply]
```

Later user and assistant replies append to the same Mem thread. Different Slack thread roots produce different Mem threads.

The dedicated thread uses:

```json
{
  "source": "slack",
  "metadata": {
    "slack_channel_id": "C123",
    "slack_thread_ts": "1723856000.000001"
  }
}
```

### Message data

Each captured message contains:

| Field | Contract |
| --- | --- |
| `role` | `user` for inbound human messages; `assistant` for Bub replies |
| `content` | Trimmed Slack text with resolved mentions when available |
| `timestamp` | Slack `ts` converted to ISO 8601 UTC, or `null` when invalid |
| `metadata.source` | `slack` |
| `metadata.source_message_id` | Slack message `ts` |
| `metadata.slack_channel_id` | Slack channel ID |
| `metadata.slack_thread_ts` | Slack root `ts`, or the message `ts` at channel root |
| `metadata.slack_user_id` | Slack user or bot ID |
| `metadata.original_url` | Slack permalink when lookup succeeds |

The append request enables deduplication and includes the Mem thread ID and Slack message `ts` in its idempotency key.

If append reports that the Mem thread does not exist, the integration creates it and supplies the initial messages. Other API failures are logged and swallowed by the capture boundary.

## Slack response

Bub Router posts the Agent's final response automatically. An ordinary response must not invoke the proactive Slack skill because that would create a duplicate message.

The destination Slack thread is taken from inbound context when available and otherwise recovered from the thread-scoped Agent session ID.

Responses longer than Slack's limit are split into chunks of at most 3,900 characters. Every chunk stays in the same Slack thread and is captured as an assistant message.

## Processing acknowledgement

When an addressed message enters the Agent path:

1. add `:hourglass:` to the inbound Slack message;
2. after the first outbound reply, remove `:hourglass:`;
3. add `:white_check_mark:`.

The acknowledgement is one-shot per Agent session response. Missing scopes, duplicate reactions, and network failures are non-fatal.

## Failure guarantees

The following operations are best-effort:

- Slack permalink lookup;
- Slack thread-root lookup;
- user mention resolution;
- Nowledge Mem capture;
- acknowledgement reactions.

A failure in one of these operations must not terminate the Socket Mode listener. In particular, a Mem failure must not prevent an addressed message from entering the Agent or prevent a generated response from being posted to Slack.

## Non-goals

The current feature does not provide:

- historical message import;
- message edit or deletion synchronization;
- file or attachment capture;
- reaction ingestion;
- channel-name enrichment;
- persistent active-thread state;
- batching, queues, or a connector-level retry system;
- a generic observer framework for other chat platforms.

## Acceptance criteria

### Ordinary channel message

Given an accepted shared-channel message without a bot mention:

- it appears in `slack:{channel_id}`;
- no Agent turn runs;
- Slack receives no bot reply or processing acknowledgement.

### New Slack thread

Given the first captured reply under a top-level Slack message:

- `slack:{channel_id}:{thread_ts}` is created;
- the fetched root precedes the first reply when root lookup succeeds;
- the reply is not duplicated in the channel Mem thread.

### Addressed Slack thread

Given a bot mention inside a Slack thread:

- the user message enters the Agent;
- the reply is posted to the same Slack thread;
- the user and assistant messages share one dedicated Mem thread;
- later plain replies in that Slack thread enter the Agent until restart.

### Isolation

Given two different Slack thread roots in one channel:

- they use different Mem thread IDs;
- they use different Bub Agent session IDs.

### Failure isolation

Given a permalink, mention, reaction, or Mem failure:

- the Socket Mode listener remains operational;
- an otherwise addressed message still reaches the Agent;
- a generated response can still be posted to Slack.
