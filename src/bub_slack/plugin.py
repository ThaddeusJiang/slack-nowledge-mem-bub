# Derived from bub-slack in bubbuild/bub-contrib and modified for Nowledge Mem capture.
"""Bub plugin entry point for the Slack channel.

Registered under the ``bub`` entry-point group as ``slack = "bub_slack.plugin"``.
Because the target is a *module* (not a callable class), Bub registers it
directly and pluggy auto-discovers the module-level ``@hookimpl`` functions
below. The channel receives ``message_handler`` while the Agent policy uses the
runtime Agent supplied in each Slack turn's state.
"""

from __future__ import annotations

from bub import hookimpl

# Importing the config module eagerly registers ``SlackSettings`` under the
# ``slack`` config section (the ``@config(name="slack")`` decorator runs at
# import time). This guarantees ``ensure_config(SlackSettings)`` inside
# ``SlackChannel.__init__`` never sees an unregistered section.
from . import config as _config  # noqa: F401
from .channel import SlackChannel

__all__ = ["provide_channels", "run_model_stream", "system_prompt"]

_SLACK_ALLOWED_TOOLS = frozenset(
    {
        "mem.connections",
        "mem.context",
        "mem.forget",
        "mem.save",
        "mem.search",
        "mem.status",
        "mem.thread",
        "mem.threads",
        "mem.timeline",
    }
)

_SLACK_RESPONSE_CONTRACT = """\
<slack_response_contract priority="highest">
When the current message metadata contains channel=$slack, Bub automatically
posts your final response to the correct Slack channel and thread.
The generic instruction saying that direct replies are ignored does NOT apply to
Slack. For a normal reply, return only the user-facing response as your final
answer; do not add a separate task completion report.

This Slack Agent is limited to the provided Nowledge Mem tools. Do not run shell
commands, read or modify files, write code, invoke skills or subagents, or fetch
external web content. If a request needs any of those capabilities, explain the
limitation instead of attempting it.

The message metadata contains mem_thread_id, the exact Nowledge Mem thread that
received the inbound Slack message. For questions about the current Slack
channel, thread, or conversation, call mem.thread with that ID directly. Do not
use mem.search or mem.threads to rediscover a known thread ID.

Use no more than two Mem tool-call rounds for one response. Then answer from the
available evidence. If the evidence is insufficient, state the limitation
instead of continuing to search.
</slack_response_contract>"""


@hookimpl
def system_prompt(prompt, state):  # type: ignore[no-untyped-def]
    """Override Bub's generic skill-send contract for inbound Slack turns."""

    if "channel=$slack" not in str(prompt):
        return ""
    return _SLACK_RESPONSE_CONTRACT


@hookimpl(tryfirst=True)
async def run_model_stream(prompt, session_id, state):  # type: ignore[no-untyped-def]
    """Run Slack turns with only the structured Nowledge Mem tools."""

    if not str(session_id).startswith("slack:"):
        return None
    agent = state.get("_runtime_agent")
    if agent is None:
        raise RuntimeError("Slack Agent policy requires the Bub runtime Agent")
    return await agent.run_stream(
        session_id=session_id,
        prompt=prompt,
        state=state,
        model=state.get("model"),
        allowed_tools=_SLACK_ALLOWED_TOOLS,
        allowed_skills=(),
    )


@hookimpl
def provide_channels(message_handler):  # type: ignore[no-untyped-def]
    """Provide the Slack channel.

    The ChannelManager filters by ``Channel.enabled``, so returning the channel
    unconditionally is safe — it is silently skipped on machines that have not
    configured both Slack tokens.
    """

    return [SlackChannel(on_receive=message_handler)]
