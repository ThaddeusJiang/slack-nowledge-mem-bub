# Slack App Setup

Use this procedure for a dedicated internal App in one target workspace. It is
compatible with the project's static `xoxb-`/`xapp-` configuration and does not
require a public Events API endpoint or an OAuth callback implementation.

## Create from the manifest

1. Confirm the exact target workspace and App display name.
2. Open Slack's App creation page and choose **From an app manifest**.
3. Select the target workspace.
4. Paste the bundled
   [Slack App manifest](https://raw.githubusercontent.com/ThaddeusJiang/slack-nowledge-mem-bub/main/.agents/skills/slack-nowledge-mem-bub-setup/assets/slack-app-manifest.yaml),
   adjusting only the App and bot display names when requested.
5. Review the non-secret summary before creating the App.

The manifest deliberately does not request `app_mentions:read`,
`chat:write.public`, or an `app_mention` subscription. The project receives
mentions through the three `message.*` events, and the bot must be invited to
each shared channel it captures.

## Required configuration

| Area | Required value |
| --- | --- |
| Socket Mode | Enabled |
| App-Level Token scope | `connections:write` |
| Bot scopes | `chat:write`, `channels:history`, `groups:history`, `im:history`, `reactions:write`, `users:read` |
| Bot events | `message.channels`, `message.groups`, `message.im` |
| App Home | Messages tab enabled and users allowed to send messages |
| Redirect URLs | Empty for this internal single-workspace setup |
| Public distribution | Disabled |

## Install and create tokens

1. Open **Install App** and verify the workspace name.
2. Immediately before the authorization write, show the requested scopes and
   obtain user confirmation.
3. Install the App. Slack generates the Bot User OAuth Token (`xoxb-...`).
4. Under **Basic Information > App-Level Tokens**, generate one token with only
   `connections:write`. Slack generates the App-Level Token (`xapp-...`).
5. The user copies both values directly to the chosen secret store. Do not read,
   transcribe, screenshot, return, or save them in memory.

Generating, regenerating, revoking, reinstalling, or uninstalling changes
external state. Do not perform those actions during a read-only audit. Never
click **Regenerate**, **Revoke**, **Uninstall**, or distribution controls unless
the user explicitly requests that exact action.

## Safe verification

Prefer labels, checked states, scope names, event names, and success URLs. If
browser snapshots are needed, discard full output and extract only allow-listed
non-secret labels. Redacting only the `xoxb-`/`xapp-` prefixes is insufficient:
Slack pages can expose other credentials such as verification tokens.

Confirm:

- App ID and selected workspace match the user's target;
- installation succeeded and a Bot User OAuth Token entry exists;
- an App-Level Token entry with `connections:write` exists;
- the six bot scopes and three bot events match exactly;
- Socket Mode and App Home messaging are enabled;
- no unrelated scope, redirect URL, or distribution mode was added.

Finally, invite the bot to every shared channel intended for capture. Channel
membership is required; do not compensate with `chat:write.public`.
