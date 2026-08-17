from __future__ import annotations

from typing import Any

import pytest

from bub_slack.nowledge import (
    NowledgeMemClient,
    _is_thread_not_found,
    capture_slack_message,
    capture_to_mem,
    slack_ts_to_iso,
)


class FakeWebClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def chat_getPermalink(self, **kwargs: str) -> dict[str, str]:
        if self.fail:
            raise RuntimeError("no permalink")
        return {"permalink": "https://workspace.slack.com/archives/C1/p1001"}


class FakeMemClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.appends: list[dict[str, Any]] = []

    async def append_message(self, **kwargs: Any) -> None:
        self.appends.append(kwargs)
        if self.fail:
            raise RuntimeError("mem unavailable")


class RecordingMemClient(NowledgeMemClient):
    def __init__(self, responses: list[dict[str, Any] | None]) -> None:
        super().__init__()
        self.responses = responses
        self.posts: list[tuple[str, dict[str, Any], bool]] = []

    async def _post(
        self, path: str, payload: dict[str, Any], *, not_found_ok: bool = False
    ) -> dict[str, Any] | None:
        self.posts.append((path, payload, not_found_ok))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_capture_appends_message_to_channel_thread() -> None:
    mem = FakeMemClient()
    await capture_to_mem(
        event={
            "text": "  customer approved launch  ",
            "channel": "C1",
            "user": "U1",
            "ts": "0.123456",
            "thread_ts": "0.000001",
        },
        web_client=FakeWebClient(),
        mem_client=mem,  # type: ignore[arg-type]
    )

    assert mem.appends == [
        {
            "thread_id": "slack:C1",
            "title": "Slack C1",
            "message": {
                "role": "user",
                "content": "customer approved launch",
                "timestamp": "1970-01-01T00:00:00.123456+00:00",
                "metadata": {
                    "source": "slack",
                    "source_message_id": "0.123456",
                    "slack_channel_id": "C1",
                    "slack_thread_ts": "0.000001",
                    "slack_user_id": "U1",
                    "original_url": "https://workspace.slack.com/archives/C1/p1001",
                },
            },
            "idempotency_key": "slack:C1:0.123456",
        }
    ]


@pytest.mark.asyncio
async def test_assistant_message_uses_same_channel_thread() -> None:
    mem = FakeMemClient()
    await capture_slack_message(
        role="assistant",
        content="answer",
        channel_id="C1",
        user_id="UBOT",
        ts="1.2",
        thread_ts="1.0",
        web_client=None,
        mem_client=mem,  # type: ignore[arg-type]
    )

    assert mem.appends[0]["thread_id"] == "slack:C1"
    assert mem.appends[0]["message"]["role"] == "assistant"
    assert mem.appends[0]["message"]["metadata"]["source"] == "slack"


@pytest.mark.asyncio
async def test_different_slack_threads_share_channel_thread() -> None:
    mem = FakeMemClient()
    for thread_ts in ("100.1", "200.1"):
        await capture_to_mem(
            event={
                "text": "hello",
                "channel": "C1",
                "ts": f"{thread_ts}1",
                "thread_ts": thread_ts,
            },
            web_client=None,
            mem_client=mem,  # type: ignore[arg-type]
        )

    assert [item["thread_id"] for item in mem.appends] == ["slack:C1", "slack:C1"]
    assert [item["message"]["metadata"]["slack_thread_ts"] for item in mem.appends] == [
        "100.1",
        "200.1",
    ]


@pytest.mark.asyncio
async def test_existing_channel_thread_uses_single_append_request() -> None:
    mem = RecordingMemClient([{"success": True}])
    message = {"role": "user", "content": "hello"}

    await mem.append_message(
        thread_id="slack:C1",
        title="Slack C1",
        message=message,
        idempotency_key="slack:C1:100.1",
    )

    assert mem.posts == [
        (
            "/threads/slack%3AC1/append",
            {
                "messages": [message],
                "deduplicate": True,
                "idempotency_key": "slack:C1:100.1",
            },
            True,
        )
    ]


@pytest.mark.asyncio
async def test_missing_channel_thread_is_created_with_first_message() -> None:
    mem = RecordingMemClient([None, {"thread": {"thread_id": "slack:C1"}}])
    message = {"role": "user", "content": "hello"}

    await mem.append_message(
        thread_id="slack:C1",
        title="Slack C1",
        message=message,
        idempotency_key="slack:C1:100.1",
    )

    assert mem.posts[1] == (
        "/threads",
        {
            "thread_id": "slack:C1",
            "title": "Slack C1",
            "messages": [message],
            "source": "slack",
            "metadata": {"slack_channel_id": "C1"},
        },
        False,
    )


@pytest.mark.asyncio
async def test_capture_failures_are_swallowed() -> None:
    mem = FakeMemClient(fail=True)
    await capture_to_mem(
        event={"text": "hello", "channel": "C1", "ts": "100.1"},
        web_client=FakeWebClient(fail=True),
        mem_client=mem,  # type: ignore[arg-type]
    )
    assert len(mem.appends) == 1


@pytest.mark.asyncio
async def test_empty_message_or_channel_is_not_captured() -> None:
    mem = FakeMemClient()
    await capture_to_mem(
        event={"text": "   ", "channel": "C1", "ts": "100.1"},
        web_client=None,
        mem_client=mem,  # type: ignore[arg-type]
    )
    await capture_to_mem(
        event={"text": "hello", "channel": "", "ts": "100.1"},
        web_client=None,
        mem_client=mem,  # type: ignore[arg-type]
    )
    assert mem.appends == []


def test_append_400_thread_not_found_triggers_create_fallback() -> None:
    assert _is_thread_not_found(400, {"detail": "Thread not found: slack:C1"})
    assert _is_thread_not_found(404, {"detail": "Thread not found"})
    assert not _is_thread_not_found(400, {"detail": "Invalid messages"})


def test_slack_ts_to_iso_rejects_invalid_values() -> None:
    assert slack_ts_to_iso("") is None
    assert slack_ts_to_iso("not-a-timestamp") is None
