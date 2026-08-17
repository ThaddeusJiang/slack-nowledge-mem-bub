"""Best-effort passive capture of Slack messages into Nowledge Mem."""

from __future__ import annotations

import os
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

        timeout = aiohttp.ClientTimeout(total=10)
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
        message: dict[str, Any],
        idempotency_key: str,
    ) -> None:
        """Append to a channel thread, creating it on the first message."""

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
                "messages": [message],
                "source": "slack",
                "metadata": {"slack_channel_id": thread_id.removeprefix("slack:")},
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
) -> None:
    """Append one Slack message without ever failing Slack message IO."""

    text = content.strip()
    if not text or not channel_id or not ts:
        return

    permalink: str | None = None
    if web_client is not None:
        try:
            result = await web_client.chat_getPermalink(
                channel=channel_id, message_ts=ts
            )
            permalink = result.get("permalink")
        except Exception:  # noqa: BLE001 — capture remains best-effort
            logger.opt(exception=True).debug("slack.capture permalink failed")

    metadata = {
        "source": "slack",
        "source_message_id": ts,
        "slack_channel_id": channel_id,
        "slack_thread_ts": thread_ts or ts,
        "slack_user_id": user_id,
    }
    if permalink:
        metadata["original_url"] = permalink

    try:
        await mem_client.append_message(
            thread_id=f"slack:{channel_id}",
            title=f"Slack {channel_id}",
            message={
                "role": role,
                "content": text,
                "timestamp": slack_ts_to_iso(ts),
                "metadata": metadata,
            },
            idempotency_key=f"slack:{channel_id}:{ts}",
        )
    except Exception as exc:  # noqa: BLE001 — Mem must not break Slack
        logger.warning("slack.capture failed: {}", exc)


async def capture_to_mem(
    *,
    event: dict[str, Any],
    web_client: Any,
    mem_client: NowledgeMemClient,
) -> None:
    """Append one inbound user message to its Slack channel thread."""

    await capture_slack_message(
        role="user",
        content=event.get("text") or "",
        channel_id=event.get("channel") or "",
        user_id=event.get("user") or "",
        ts=event.get("ts") or "",
        thread_ts=event.get("thread_ts") or "",
        web_client=web_client,
        mem_client=mem_client,
    )
