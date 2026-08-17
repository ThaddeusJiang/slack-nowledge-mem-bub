"""Bub plugin entry point for the Slack channel.

Registered under the ``bub`` entry-point group as ``slack = "bub_slack.plugin"``.
Because the target is a *module* (not a callable class), Bub registers it
directly and pluggy auto-discovers the module-level ``@hookimpl`` functions
below. The channel needs only ``message_handler`` — no framework reference.
"""

from __future__ import annotations

from bub import hookimpl

# Importing the config module eagerly registers ``SlackSettings`` under the
# ``slack`` config section (the ``@config(name="slack")`` decorator runs at
# import time). This guarantees ``ensure_config(SlackSettings)`` inside
# ``SlackChannel.__init__`` never sees an unregistered section.
from . import config as _config  # noqa: F401
from .channel import SlackChannel

__all__ = ["provide_channels", "system_prompt"]

_SLACK_RESPONSE_CONTRACT = """\
<slack_response_contract priority="highest">
When the current message metadata contains channel=$slack, Bub automatically
posts your final response to the correct Slack channel and thread.
The generic instruction saying that direct replies are ignored does NOT apply to
Slack. For a normal reply, do NOT call the slack skill or slack_send.py. Return
only the user-facing response as your final answer; do not add a separate task
completion report. Use the slack skill only for genuinely proactive or
out-of-band messages to a different destination, or for edits and reactions.
</slack_response_contract>"""


@hookimpl
def system_prompt(prompt, state):  # type: ignore[no-untyped-def]
    """Override Bub's generic skill-send contract for inbound Slack turns."""

    if "channel=$slack" not in str(prompt):
        return ""
    return _SLACK_RESPONSE_CONTRACT


@hookimpl
def provide_channels(message_handler):  # type: ignore[no-untyped-def]
    """Provide the Slack channel.

    The ChannelManager filters by ``Channel.enabled``, so returning the channel
    unconditionally is safe — it is silently skipped on machines that have not
    configured both Slack tokens.
    """

    return [SlackChannel(on_receive=message_handler)]
