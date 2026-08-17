"""Best-effort passive capture of Slack messages into Nowledge Mem."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import aiohttp
from loguru import logger


class NowledgeMemClient:
    """Minimal client for appending Slack messages to Mem threads."""

    def __init__(self) -> None:
        self._api_url = os.getenv("NMEM_API_URL", "http://127.0.0.1:14242").rstrip("/")
        self._api_key = os.getenv("NMEM_API_KEY", "").strip()

    async def _post(
        self, path: str, payload: dict[str, Any], *, not_found_ok: bool = False
    ) -> dict[str, Any] | None:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-NMEM-API-Key"] = self._api_key

        # Thread creation can include local indexing and occasionally exceeds the
        # old 10-second budget. Keep connect failures short while allowing the
        # local Mem server enough time to finish a committed write.
        timeout = aiohttp.ClientTimeout(total=30, connect=5)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                f"{self._api_url}{path}", json=payload, headers=headers
            ) as response,
        ):
            if not_found_ok and response.status in {400, 404}:
                error = await response.json()
                if _is_thread_not_found(response.status, error):
                    return None
            response.raise_for_status()
            result = await response.json()
            return result if isinstance(result, dict) else {}

    async def append_message(
        self,
        *,
        thread_id: str,
        title: str,
        thread_metadata: dict[str, Any],
        message: dict[str, Any],
        idempotency_key: str,
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        """Append to a Slack-backed thread, creating it on the first message."""

        encoded_id = quote(thread_id, safe="")
        result = await self._post(
            f"/threads/{encoded_id}/append",
            {
                "messages": [message],
                "deduplicate": True,
                "idempotency_key": idempotency_key,
            },
            not_found_ok=True,
        )
        if result is not None:
            return

        await self._post(
            "/threads",
            {
                "thread_id": thread_id,
                "title": title,
                "messages": initial_messages or [message],
                "source": "slack",
                "metadata": thread_metadata,
            },
        )


def _is_thread_not_found(status: int, payload: Any) -> bool:
    if status not in {400, 404} or not isinstance(payload, dict):
        return False
    return str(payload.get("detail") or "").startswith("Thread not found")


def slack_ts_to_iso(ts: str) -> str | None:
    """Convert Slack's Unix timestamp to an ISO 8601 UTC timestamp."""

    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=UTC).isoformat()
    except (TypeError, ValueError, OSError):
        return None


async def _slack_permalink(web_client: Any, channel_id: str, ts: str) -> str | None:
    if web_client is None:
        return None
    try:
        result = await web_client.chat_getPermalink(channel=channel_id, message_ts=ts)
        return result.get("permalink")
    except Exception:  # noqa: BLE001 — provenance enrichment is best-effort
        logger.opt(exception=True).debug("slack.capture permalink failed")
        return None


def _mem_message(
    *,
    role: str,
    content: str,
    channel_id: str,
    user_id: str,
    ts: str,
    thread_ts: str,
    permalink: str | None,
) -> dict[str, Any]:
    metadata = {
        "source": "slack",
        "source_message_id": ts,
        "slack_channel_id": channel_id,
        "slack_thread_ts": thread_ts or ts,
        "slack_user_id": user_id,
    }
    if permalink:
        metadata["original_url"] = permalink
    return {
        "role": role,
        "content": content.strip(),
        "timestamp": slack_ts_to_iso(ts),
        "metadata": metadata,
    }


async def _fetch_thread_root(
    *,
    channel_id: str,
    thread_ts: str,
    web_client: Any,
    resolve_mentions: Callable[[str], Awaitable[str]] | None = None,
) -> dict[str, Any] | None:
    """Fetch the Slack root so a newly created Mem thread is self-contained."""

    if web_client is None or not thread_ts:
        return None
    try:
        result = await web_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=1,
            inclusive=True,
        )
        messages = result.get("messages") or []
        root = next(
            (item for item in messages if (item.get("ts") or "") == thread_ts),
            None,
        )
        if root is None or not (root.get("text") or "").strip():
            return None
        root_text = root.get("text") or ""
        if resolve_mentions is not None:
            try:
                root_text = await resolve_mentions(root_text)
            except Exception:  # noqa: BLE001 — keep the raw root as fallback
                logger.opt(exception=True).debug(
                    "slack.capture thread root mention enrichment failed"
                )
        permalink = await _slack_permalink(web_client, channel_id, thread_ts)
        is_bot = bool(root.get("bot_id") or root.get("bot_profile"))
        return _mem_message(
            role="assistant" if is_bot else "user",
            content=root_text,
            channel_id=channel_id,
            user_id=root.get("user") or root.get("bot_id") or "",
            ts=thread_ts,
            thread_ts=thread_ts,
            permalink=permalink,
        )
    except Exception:  # noqa: BLE001 — root enrichment must not block capture
        logger.opt(exception=True).debug("slack.capture thread root failed")
        return None


async def capture_slack_message(
    *,
    role: str,
    content: str,
    channel_id: str,
    user_id: str,
    ts: str,
    thread_ts: str,
    web_client: Any,
    mem_client: NowledgeMemClient,
    resolve_mentions: Callable[[str], Awaitable[str]] | None = None,
) -> None:
    """Append one Slack message without ever failing Slack message IO."""

    text = content.strip()
    if not text or not channel_id or not ts:
        return

    permalink = await _slack_permalink(web_client, channel_id, ts)
    message = _mem_message(
        role=role,
        content=text,
        channel_id=channel_id,
        user_id=user_id,
        ts=ts,
        thread_ts=thread_ts,
        permalink=permalink,
    )

    if thread_ts:
        mem_thread_id = f"slack:{channel_id}:{thread_ts}"
        title = f"Slack {channel_id} thread {thread_ts}"
        thread_metadata = {
            "slack_channel_id": channel_id,
            "slack_thread_ts": thread_ts,
        }
    else:
        mem_thread_id = f"slack:{channel_id}"
        title = f"Slack {channel_id}"
        thread_metadata = {"slack_channel_id": channel_id}

    initial_messages: list[dict[str, Any]] | None = None
    if thread_ts and thread_ts != ts:
        root_message = await _fetch_thread_root(
            channel_id=channel_id,
            thread_ts=thread_ts,
            web_client=web_client,
            resolve_mentions=resolve_mentions,
        )
        if root_message is not None:
            initial_messages = [root_message, message]

    try:
        await mem_client.append_message(
            thread_id=mem_thread_id,
            title=title,
            thread_metadata=thread_metadata,
            message=message,
            idempotency_key=f"{mem_thread_id}:{ts}",
            initial_messages=initial_messages,
        )
    except Exception as exc:  # noqa: BLE001 — Mem must not break Slack
        logger.opt(exception=True).warning(
            "slack.capture failed error_type={} error={!r}",
            type(exc).__name__,
            exc,
        )


async def capture_to_mem(
    *,
    event: dict[str, Any],
    web_client: Any,
    mem_client: NowledgeMemClient,
    resolve_mentions: Callable[[str], Awaitable[str]] | None = None,
) -> None:
    """Append one inbound user message to its channel or Slack thread."""

    await capture_slack_message(
        role="user",
        content=event.get("text") or "",
        channel_id=event.get("channel") or "",
        user_id=event.get("user") or "",
        ts=event.get("ts") or "",
        thread_ts=event.get("thread_ts") or "",
        web_client=web_client,
        mem_client=mem_client,
        resolve_mentions=resolve_mentions,
    )
