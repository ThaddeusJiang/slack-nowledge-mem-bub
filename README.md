# slack-nowledge-mem-bub

最小可运行的 Bub Slack Team Memory：

```text
普通 Slack 消息 → Nowledge Mem → 不调用 Agent、不回复
@Bot 消息        → Nowledge Mem → Bub Agent → Slack 回复
```

本仓库是 [`bub-slack`](https://github.com/bubbuild/bub-contrib/tree/main/packages/bub-slack) 的最小 fork，基于上游提交 `f75245543dd24a713a8d330bbcbff1c78b5f5ad2`，只在现有消息处理路径中增加 Passive Capture。Bub Core 与 [`nowledge-mem-bub`](https://github.com/nowledge-co/community/tree/main/nowledge-mem-bub-plugin) 不做修改。

## 行为

| Slack 消息 | 更新 Mem Thread | 进入 Bub Agent |
| --- | --- | --- |
| Channel 顶层普通消息 | 是，Channel Mem Thread | 否 |
| Channel 顶层 `@Bot` | 是，Channel Mem Thread | 是 |
| Slack Thread 中的 user reply | 是，独立 Mem Thread | Bot 已参与或被 mention 时是 |
| Slack Thread 中的 Bot reply | 是，与 user reply 相同的 Mem Thread，`role=assistant` | — |
| DM 顶层消息 | 是，Channel Mem Thread | 是（沿用 bub-slack 行为） |
| Socket 回流的 bot/self/subtype 消息 | 否，避免重复 | 否 |
| allow-list 外消息 | 否 | 否 |

Slack 顶层消息固定写入 Channel Mem Thread：

```text
slack:{channel_id}
```

Slack Thread reply（user 或 Bot）按 Slack Thread root 单独映射：

```text
slack:{channel_id}:{thread_ts}
```

根消息首先保存在 Channel Mem Thread；出现第一条 reply 时，通过 Slack `conversations.replies` 读取根消息，并以 `[root, first reply]` 创建独立 Mem Thread，使 Thread 上下文完整。之后的 user / Bot reply 只追加到该独立 Thread。用户消息和 Bub Agent 回复都使用 `POST /threads/{thread_id}/append`；Slack `ts` 用作 idempotency key。Message metadata 保存 `source_message_id`、`slack_channel_id`、`slack_thread_ts`、`slack_user_id` 和可选的 `original_url`；独立 Thread metadata 额外保存 `slack_thread_ts`。Thread 来源始终是 `slack`。

Slack event 中的 `<@USER_ID>` 会通过 `users.info` 转换为 Slack 当前显示名（例如 `@tj2`）后再写入 Mem 和交给 Agent；首次创建独立 Mem Thread 时回填的 root 也复用同一解析路径。解析结果在进程内缓存；API 失败时保留原始 token。

Passive Capture 是 best-effort：permalink 或 Mem 写入失败只记录日志，不会阻止已 `@Bot` 的消息进入 Agent。

普通 Agent 回复由 Bub Router 自动发送到正确的 Slack Thread；Agent 不应调用 `slack_send.py`，否则会与自动回复重复。Slack skill 仅用于跨目标主动消息、编辑和 reaction。

## 安装

要求 Python 3.12+、可用的 Nowledge Mem 服务，以及已安装的 `nmem` CLI（供 Agent 插件使用）：

```bash
pip install nmem-cli
nmem status

uv sync
```

`uv sync` 会安装：

- Bub
- 本仓库的 `bub-slack`
- `nowledge-mem-bub`

## 配置

复制环境变量示例：

```bash
cp .env.example .env
```

必须配置 Slack Socket Mode tokens 和 Bub 所用模型的 API key。Nowledge Mem 本地服务默认使用 `http://127.0.0.1:14242`；远程服务再设置 `NMEM_API_URL` / `NMEM_API_KEY`。保持 `NMEM_SESSION_DIGEST=0`，避免 `nowledge-mem-bub` 再创建一份 `source=bub` 的 Session Thread。

Slack App：

1. 开启 **Socket Mode**，App Token 添加 `connections:write`。
2. **OAuth & Permissions** Bot Scopes 添加 `chat:write`、`app_mentions:read`、`channels:history`、`groups:history`、`im:history`、`reactions:write`、`users:read`（解析 mention 显示名）。
3. Event Subscriptions 添加 `message.channels`、`message.groups`、`message.im`、`app_mention`。
4. 将 Bot 邀请到需要监听的 Channel。

可用 `BUB_SLACK_ALLOW_CHANNELS` / `BUB_SLACK_ALLOW_USERS` 限制 Agent 与 Passive Capture 的范围。

## 运行与验证

```bash
uv run bub hooks   # nowledge_mem 应挂载到相关 hooks
uv run bub gateway
uv run bub onboard
```

1. 在 Channel 发送不含 `@Bot` 的唯一文本：Bot 不应回复；`nmem t show slack:{channel_id}` 应包含该消息。
2. 对该消息创建 Slack Thread 并回复：`nmem t show slack:{channel_id}:{thread_ts}` 的第一、二条消息应依次为 root 和 first reply；Channel Mem Thread 不应重复新增 reply。
3. 在 Slack Thread 中 `@Bot`：user reply 和 Agent 的 `role=assistant` reply 应写入同一个独立 Mem Thread，不应新增 `source=bub` Thread。
4. 在同一 Channel 的两个 Slack Thread 回复：应创建两个不同的 Mem Thread。
5. 检查 Message 的 `metadata.original_url` 可返回原 Slack Message。

## 开发

```bash
uv run pytest -q
uv build
```

MVP 不处理历史导入、消息编辑/删除、附件、批处理、队列或重试；验证 Passive Capture 的价值后再考虑这些能力。
