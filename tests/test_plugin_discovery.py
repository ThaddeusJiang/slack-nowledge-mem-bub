# Derived from bub-slack in bubbuild/bub-contrib and modified for this project.
from __future__ import annotations

import importlib.metadata

import nowledge_mem_bub  # noqa: F401  # registers the mem.* tools
import pytest
from bub.configure import CONFIG_MAP
from bub.tools import REGISTRY

import bub_slack
import bub_slack.plugin as plugin_mod
from bub_slack.channel import SlackChannel


def test_provide_channels_returns_one_slack_channel() -> None:
    sentinel = object()
    channels = plugin_mod.provide_channels(sentinel)  # type: ignore[arg-type]
    assert len(channels) == 1
    ch = channels[0]
    assert isinstance(ch, SlackChannel)
    assert ch.name == "slack"
    assert ch._on_receive is sentinel


def test_system_prompt_overrides_generic_channel_send_for_slack() -> None:
    prompt = plugin_mod.system_prompt("channel=$slack|chat_id=C1", {})
    assert "automatically" in prompt
    assert "limited to the provided Nowledge Mem tools" in prompt
    assert "shell" in prompt
    assert "external web content" in prompt
    assert "completion report" in prompt
    assert "mem_thread_id" in prompt
    assert "call mem.thread with that ID directly" in prompt
    assert "no more than two Mem tool-call rounds" in prompt


@pytest.mark.asyncio
async def test_slack_agent_is_limited_to_mem_tools_and_no_skills() -> None:
    calls: list[dict[str, object]] = []
    sentinel = object()

    class Agent:
        async def run_stream(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return sentinel

    state = {"_runtime_agent": Agent(), "model": "test:model"}
    result = await plugin_mod.run_model_stream("prompt", "slack:C1", state)

    assert result is sentinel
    assert calls == [
        {
            "session_id": "slack:C1",
            "prompt": "prompt",
            "state": state,
            "model": "test:model",
            "allowed_tools": plugin_mod._SLACK_ALLOWED_TOOLS,
            "allowed_skills": (),
        }
    ]
    assert all(name.startswith("mem.") for name in plugin_mod._SLACK_ALLOWED_TOOLS)
    assert "bash" not in plugin_mod._SLACK_ALLOWED_TOOLS
    assert "web.fetch" not in plugin_mod._SLACK_ALLOWED_TOOLS
    assert plugin_mod._SLACK_ALLOWED_TOOLS <= REGISTRY.keys()


@pytest.mark.asyncio
async def test_tool_limit_does_not_take_over_non_slack_sessions() -> None:
    assert await plugin_mod.run_model_stream("prompt", "cli:local", {}) is None


@pytest.mark.asyncio
async def test_slack_tool_limit_fails_closed_without_runtime_agent() -> None:
    with pytest.raises(RuntimeError, match="requires the Bub runtime Agent"):
        await plugin_mod.run_model_stream("prompt", "slack:C1", {})


def test_system_prompt_does_not_affect_other_channels() -> None:
    assert plugin_mod.system_prompt("channel=$cli", {}) == ""


def test_importing_plugin_registers_slack_settings() -> None:
    # The eager ``from . import config`` in plugin.py registers SlackSettings
    # under the "slack" config section at import time.
    assert "slack" in CONFIG_MAP
    registered = CONFIG_MAP["slack"]
    # CONFIG_MAP maps section name -> list of registered settings classes.
    classes = registered if isinstance(registered, list) else [registered]
    assert any(c.__name__ == "SlackSettings" for c in classes)


def test_runtime_version_matches_distribution_metadata() -> None:
    assert bub_slack.__version__ == importlib.metadata.version("bub-slack")


def test_entry_point_registered() -> None:
    # Only meaningful once the package is installed (editable or otherwise).
    try:
        eps = importlib.metadata.entry_points(group="bub")
    except Exception:  # noqa: BLE001  # pragma: no cover
        return
    names = [ep.name for ep in eps]
    if "slack" in names:
        ep = next(e for e in eps if e.name == "slack")
        assert ep.value == "bub_slack.plugin"
