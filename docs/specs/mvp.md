# Bub + bub-slack + Nowledge Mem：全面监听 Slack Message 的 MVP 实现方案

refs
- https://github.com/bubbuild/bub
- https://github.com/bubbuild/bub-contrib/tree/main/packages/bub-slack
- https://github.com/nowledge-co/community/blob/main/nowledge-mem-bub-plugin

> 实现校正（Nowledge Mem API 0.10.63）：Passive Capture 不再逐条调用
> `POST /memories`。Slack Channel 顶层消息写入固定 Mem Thread
> `slack:{channel_id}`；Slack Thread 中的 user / Bot reply 写入独立 Mem Thread
> `slack:{channel_id}:{thread_ts}`。根消息先写入 Channel Mem Thread；出现第一条
> reply 时，通过 Slack `conversations.replies` 读取 root，并用 `[root, reply]`
> 创建独立 Thread，后续 reply 再通过 `/threads/{thread_id}/append` 追加。Slack
> message/thread/user id 与 permalink 保存在
> Message metadata。Slack `<@USER_ID>` 通过 `users.info` 转为当前显示名后写入
> content。部署时设置 `NMEM_SESSION_DIGEST=0`，避免 plugin 另外创建
> `source=bub` Thread。

## 1. 目标

实现一个基于现有 Bub 生态的 Slack Team Memory MVP。

目标行为：

```text
普通 Slack 消息
→ 自动写入 Nowledge Mem
→ 不调用 LLM
→ 不回复

@Nowledge 消息
→ 进入 Bub Agent
→ 使用 mem.search / mem.save
→ 回复 Slack
```

整体原则：

> **所有 Slack 消息都进入 Memory，只有明确交给 Bot 的消息才进入 Agent。**

## 2. 使用现有组件

直接复用三个已有组件：

```text
Bub
→ Agent Runtime / Turn Pipeline

bub-slack
→ Slack Socket Mode
→ Slack Event 接收
→ Thread / DM / @mention
→ Slack 回复

nowledge-mem-bub-plugin
→ mem.search
→ mem.save
→ mem.context
→ mem.timeline
→ Session Digest
→ Nowledge Mem 连接
```

现有 Agent 交互链路不改：

```text
Slack @Nowledge
      ↓
bub-slack
      ↓
Bub
      ↓
nowledge-mem-bub-plugin
      ↓
Bub Agent
      ↓
mem.search / mem.save
      ↓
Nowledge Mem
```

只增加一条 Passive Capture 支线。

## 3. 最终架构

```text
                         Slack
                           │
                           │ Socket Mode Event
                           ▼
                     ┌───────────┐
                     │ bub-slack │
                     └─────┬─────┘
                           │
                    基础消息过滤
                bot / subtype / self
                           │
                           ▼
                  Passive Capture
                           │
                           ▼
                    POST /memories
                           │
                           ▼
                    Nowledge Mem
                           │
                           │
                    addressed ?
                    /          \
                  No            Yes
                  │              │
                  ▼              ▼
                return          Bub
                                 │
                          Turn Pipeline
                                 │
                       nowledge-mem-bub
                                 │
                          Bub Agent / LLM
                                 │
                     mem.search / mem.save
                                 │
                                 ▼
                           Nowledge Mem
                                 │
                                 ▼
                         bub-slack.send()
                                 │
                                 ▼
                               Slack
```

## 4. 为什么修改 bub-slack

当前 `bub-slack` 的关键逻辑：

```python
addressed = (
    channel_type == "im"
    or mentioned
    or in_active_thread
)

if not addressed:
    return
```

因此普通 Channel Message：

```text
田中：
客户决定周五上线
```

如果没有 `@Bot`：

```text
Slack
↓
bub-slack
↓
return
```

它甚至不会进入 Bub。

所以 Passive Capture 必须发生在：

```python
if not addressed:
    return
```

之前。

## 5. MVP 实现策略

第一版直接 fork：

```text
bubbuild/bub-contrib
```

只修改：

```text
packages/bub-slack
```

暂时不要：

* 新设计 Bub Hook
* 新建 Channel abstraction
* 修改 Bub Core
* 修改 Agent Pipeline
* 让普通消息进入 LLM
* 做通用 Slack Plugin Framework

目标只是最快验证：

> Slack 团队信息持续进入 Nowledge Mem 是否有价值。

## 6. Passive Capture 插入位置

建议放在现有基础过滤之后。

伪代码：

```python
async def _handle_message(self, event):
    # Existing
    if event.get("subtype"):
        return

    # Existing
    if event.get("bot_id") or event.get("bot_profile"):
        return

    user_id = event.get("user") or ""

    # Existing
    if self._bot_user_id and user_id == self._bot_user_id:
        return

    # NEW
    await capture_to_mem(event)

    # Existing logic continues
    channel_id = event.get("channel") or ""
    text = (event.get("text") or "").strip()
    channel_type = event.get("channel_type") or ""
    ts = event.get("ts") or ""
    thread_ts = event.get("thread_ts") or ""

    mention = f"<@{self._bot_user_id}>" if self._bot_user_id else ""
    mentioned = bool(mention) and mention in text

    in_active_thread = (
        bool(thread_ts)
        and thread_ts in self._active_threads
    )

    addressed = (
        channel_type == "im"
        or mentioned
        or in_active_thread
    )

    if not addressed:
        return

    # Existing Bub Agent flow
    ...
```

这样普通消息：

```text
Slack
↓
capture_to_mem()
↓
Nowledge Mem
↓
addressed = false
↓
return
```

而 `@Nowledge`：

```text
Slack
↓
capture_to_mem()
↓
Nowledge Mem
↓
addressed = true
↓
Bub Agent
```

## 7. Memory 数据设计

MVP 不需要主动生成：

```text
title
labels
entities
importance
topic
```

这些可以交给 Nowledge Mem 后台 AI。

Connector 只负责提供**无法可靠推断的 provenance**。

建议写入：

```json
{
  "content": "客户决定 Pricing Page 下周上线",
  "source": "slack",
  "source_thread_id": "1723856000.000001",
  "source_message_id": "1723856172.123456",
  "original_url": "https://workspace.slack.com/archives/C123/p...",
  "event_start": "2026-08-17T10:30:00+09:00"
}
```

字段职责：

```text
content
→ 原始 Slack Message

source
→ slack

source_message_id
→ Slack message ts

source_thread_id
→ thread_ts
→ 如果没有 thread，则使用当前 ts

original_url
→ Slack permalink

event_start
→ Slack ts 转 ISO 8601
```

## 8. Slack ID 映射

普通 Top-level Message：

```text
ts = 1723856172.123456
thread_ts = null
```

映射：

```text
source_message_id
= 1723856172.123456

source_thread_id
= 1723856172.123456
```

Thread Reply：

```text
thread_ts = 1723856000.000001
ts        = 1723856172.123456
```

映射：

```text
source_thread_id
= 1723856000.000001

source_message_id
= 1723856172.123456
```

这样 Nowledge 可以知道：

```text
哪个 Thread
↓
包含哪些 Message
```

## 9. Original URL

建议通过 Slack API 获取 permalink。

逻辑：

```python
response = await self._web_client.chat_getPermalink(
    channel=channel_id,
    message_ts=ts,
)

permalink = response.get("permalink")
```

如果失败：

```text
不要阻塞消息处理
```

返回：

```python
None
```

即可。

MVP 中 permalink 获取失败不应该影响 Capture。

## 10. 时间转换

Slack：

```text
1723856172.123456
```

转换为 ISO 8601：

```python
from datetime import datetime, timezone

def slack_ts_to_iso(ts: str) -> str:
    return datetime.fromtimestamp(
        float(ts),
        tz=timezone.utc,
    ).isoformat()
```

例如：

```text
2026-08-17T01:30:00+00:00
```

UTC 即可，不需要强制转换 JST。

## 11. `capture_to_mem`

推荐单独放文件：

```text
packages/bub-slack/src/bub_slack/nowledge.py
```

例如：

```python
from datetime import datetime, timezone

from loguru import logger


def slack_ts_to_iso(ts: str) -> str | None:
    if not ts:
        return None

    try:
        return datetime.fromtimestamp(
            float(ts),
            tz=timezone.utc,
        ).isoformat()
    except (TypeError, ValueError):
        return None


async def capture_to_mem(
    *,
    event: dict,
    web_client,
    mem_client,
) -> None:
    text = (event.get("text") or "").strip()

    if not text:
        return

    channel_id = event.get("channel") or ""
    ts = event.get("ts") or ""
    thread_ts = event.get("thread_ts") or ""

    permalink = None

    if channel_id and ts:
        try:
            result = await web_client.chat_getPermalink(
                channel=channel_id,
                message_ts=ts,
            )
            permalink = result.get("permalink")
        except Exception:
            logger.debug(
                "failed to fetch slack permalink"
            )

    try:
        await mem_client.create_memory(
            content=text,
            source="slack",
            source_thread_id=thread_ts or ts,
            source_message_id=ts,
            original_url=permalink,
            event_start=slack_ts_to_iso(ts),
        )
    except Exception as exc:
        logger.warning(
            "slack passive capture failed: {}",
            exc,
        )
```

关键原则：

```text
Capture Failure
≠
Slack Bot Failure
```

所以：

```python
capture_to_mem()
```

永远不要向上抛异常导致 Socket listener 出错。

## 12. Mem Client

这里有两个选择。

### 方案 A：复用 nmem CLI

如果 `nmem CLI` 已经支持：

```text
source
source_thread_id
source_message_id
original_url
```

则扩展现有：

```python
NmemClient.add_memory()
```

即可。

理想接口：

```python
async def add_memory(
    self,
    content: str,
    *,
    source: str = "bub",
    source_thread_id: str | None = None,
    source_message_id: str | None = None,
    original_url: str | None = None,
    event_start: str | None = None,
) -> dict:
    ...
```

Passive Capture：

```python
await _nmem.add_memory(
    content=text,
    source="slack",
    source_thread_id=thread_ts or ts,
    source_message_id=ts,
    original_url=permalink,
    event_start=event_start,
)
```

### 方案 B：直接调用 POST /memories

如果 nmem CLI 暂时没有完整暴露 provenance：

> **MVP 直接 HTTP 调 `/memories`。**

不要为了复用 CLI 丢失：

```text
source_thread_id
source_message_id
original_url
```

调用：

```text
POST /memories
```

Body：

```json
{
  "content": "客户决定周五上线",
  "source": "slack",
  "source_thread_id": "1723856000.000001",
  "source_message_id": "1723856172.123456",
  "original_url": "https://...",
  "event_start": "2026-08-17T01:30:00+00:00"
}
```

从数据正确性角度，我更推荐：

> **API 能保存完整 provenance，就优先 API。**

## 13. 配置

Bub / Slack：

```env
BUB_SLACK_BOT_TOKEN=xoxb-...
BUB_SLACK_APP_TOKEN=xapp-...
```

可选限制：

```env
BUB_SLACK_ALLOW_CHANNELS=C123,C456
BUB_SLACK_ALLOW_USERS=U123,U456
```

Nowledge Mem：

```env
NMEM_API_URL=http://nowledge-mem:8000
NMEM_API_KEY=...
```

Agent：

```env
# 根据 Bub 当前使用的模型 Provider 配置
OPENAI_API_KEY=...
```

Nowledge Plugin：

```env
NMEM_SESSION_CONTEXT=0
NMEM_SESSION_DIGEST=0
```

MVP 我建议：

```text
NMEM_SESSION_CONTEXT=0
```

原因：

普通历史查询让 Agent：

```text
mem.search
```

按需搜索即可。

无需每一轮自动加载 Memory，避免额外开销。

## 14. 安装依赖

Fork：

```bash
git clone https://github.com/<your-org>/bub-contrib.git
```

安装修改后的 Slack：

```bash
uv pip install -e packages/bub-slack
```

安装 Bub：

```bash
uv pip install bub
```

安装 Nowledge Plugin：

```bash
uv pip install \
  "nowledge-mem-bub @ git+https://github.com/nowledge-co/community.git#subdirectory=nowledge-mem-bub-plugin"
```

如果使用本地代码：

```bash
uv pip install -e ./nowledge-mem-bub-plugin
```

## 15. Slack App 配置

Socket Mode：

```text
Enabled
```

App Token：

```text
connections:write
```

Bot Scopes 至少：

```text
chat:write
app_mentions:read
channels:history
groups:history
im:history
reactions:write
users:read
```

为了获取 permalink：

```text
channels:history / groups:history
```

通常现有权限即可。

Event Subscriptions：

```text
message.channels
message.groups
message.im
app_mention
```

然后：

```text
Invite Bot
→ target channels
```

## 16. 运行

启动 Bub Gateway：

```bash
bub gateway
```

调用链：

```text
bub gateway
   ↓
load plugins
   ↓
bub-slack provide_channels()
   ↓
SlackChannel.start()
   ↓
Socket Mode Connected
```

同时：

```text
nowledge-mem-bub
```

会作为 Bub plugin 被自动加载。

## 17. 完整执行顺序

### 普通消息

```text
User
 ↓
Slack
 ↓
Socket Mode
 ↓
bub-slack._on_slack_event()
 ↓
bub-slack._handle_message()
 ↓
过滤 bot / subtype
 ↓
capture_to_mem()
 ↓
POST /memories
 ↓
Nowledge Mem
 ↓
addressed = false
 ↓
return
```

不会：

```text
运行 LLM
产生回复
进入 Bub Agent
```

### @Nowledge

```text
User
 ↓
@Nowledge 客户什么时候决定周五上线？
 ↓
Slack
 ↓
bub-slack
 ↓
capture_to_mem()
 ↓
Nowledge Mem
 ↓
addressed = true
 ↓
ChannelMessage
 ↓
Bub
 ↓
nowledge-mem-bub.system_prompt()
 ↓
nowledge-mem-bub.build_prompt()
 ↓
Bub Agent
 ↓
mem.search
 ↓
Nowledge Mem
 ↓
Tool Result
 ↓
Bub Agent
 ↓
Answer
 ↓
nowledge-mem-bub.save_state()
 ↓
Nowledge Mem Thread
 ↓
bub-slack.send()
 ↓
Slack
```

## 18. MVP 验收

### Test 1：Passive Capture

Slack：

```text
田中：
客户确认 Pricing Page 下周发布。
```

没有 `@Nowledge`。

预期：

```text
Slack Bot 不回复
```

但 Nowledge Mem：

```text
可以搜索：
Pricing Page 下周发布
```

并且 Memory 有：

```text
source = slack
source_message_id
source_thread_id
original_url
event_start
```

### Test 2：Agent Recall

Slack：

```text
@Nowledge
Pricing Page 最后什么时候发布？
```

预期：

```text
Bub Agent
↓
mem.search
↓
找到刚才自动 Capture 的 Memory
↓
回答
```

### Test 3：Thread

Thread：

```text
田中：
Pricing Page 周五发布

佐藤：
客户要求改到下周一
```

两条 Memory：

```text
source_thread_id
```

相同。

```text
source_message_id
```

不同。

### Test 4：Original URL

Nowledge Memory：

```text
original_url
```

点击后可以直接回到对应 Slack Message。

## 19. MVP 暂时不要做

* Slack 历史消息批量导入
* Channel 名称 enrichment
* Attachment
* File
* Reactions
* Message edit 同步
* Delete 同步
* Batch ingestion
* Queue
* Retry 系统
* Rate Limit 优化
* 自动 summary
* 自动 labels
* 自定义 Bub Hook
* Telegram / Discord

这些都等 MVP 验证后再做。

## 20. 后续第二阶段

MVP 成功以后，再把：

```python
await capture_to_mem(event)
```

抽象成：

```text
Channel Message Observer
```

最终：

```text
Slack ───────┐
Telegram ────┤
Discord ─────┤
Teams ───────┘
      ↓
Bub Channels
      ↓
Passive Capture
      ↓
Nowledge Mem
```

这样 Nowledge Mem 就真正成为：

> **跨平台持续成长的 Team Memory。**

而 Bub 继续负责：

> **只有用户真正需要 AI 时，才启动 Agent。**
