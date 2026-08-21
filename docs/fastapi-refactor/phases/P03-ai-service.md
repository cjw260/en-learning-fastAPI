# P03：AI 服务迁移

状态：`COMPLETED`

## 启动条件

P02 完成并推送；新的执行重新加载 skill 和 framework parity；阶段锁为 P03。

## 目标与外部效果

FastAPI 在 `/ai/v1` 提供 prompt 列表、聊天 SSE 和聊天历史；前端看到的 reasoning/chat 流与现有体验兼容，身份安全和错误处理得到修复。

## 实现步骤

1. 从旧 prompt mode 建立可测试的角色配置，迁移 `/prompt/list`。
2. 用 Pydantic 验证 chat 请求、角色枚举、消息长度和功能开关；Bearer token 决定用户身份。
3. 封装普通/推理 LLM 和联网搜索，设置连接、首 token、总耗时、取消和有限重试。
4. 使用 `StreamingResponse` 输出 SSE，保持 reasoning/chat JSON 载荷；设置禁缓冲 header 和可选心跳。
5. 客户端断开时取消上游生成并释放连接；流开始后的错误转成受控 SSE 事件/结束语义。
6. 建立新 checkpoint/history 表并按 user+role 隔离；不迁移旧历史。
7. `/chat/history` 只读取当前用户数据，保持前端数组形状和消息顺序。
8. 使用 mock LLM、故障注入和浏览器完成契约与体验验证；只准备 AI 灰度配置，不改生产。

## 验收标准

- [x] `/ai/v1` 路径、方法、prompt/chat/history schema 兼容。
- [x] reasoning/chat 分片、顺序、结束和 header 正确。
- [x] 断连、超时、上游失败、无效角色和超长输入受控。
- [x] AI 身份不可由 body/query userId 越权伪造。
- [x] 新历史持久、隔离、重启可恢复；旧历史为空已记录。
- [x] 日志不含密钥或完整敏感对话。
- [x] 前端普通/深度思考/历史浏览器验证通过。
- [x] 未实现 Core 业务、支付、Socket.IO 或 worker。

## 回退

将 Nginx `/ai/` upstream 指回 NestJS :3001；新历史表独立保留。准备好的 AI-only
灰度、观察和回退步骤见 `../runbooks/P03-ai-canary.md`，本阶段不执行生产变更。

## 已锁定的 P03 契约与安全边界

- prompt 顺序保持 `normal/master/business/qilinge/xiaoman`，路径和成功 envelope 不变。
- chat 请求保留 `deepThink/webSearch/role/content/userId`，但 JWT access token 是唯一身份来源。
- chat SSE 仅输出旧前端认识的 reasoning/chat data 帧；心跳使用 SSE 注释，不污染消息解析。
- history 返回按 position 升序的 `{role, content, reasoning?}` 数组；user+role 隔离，旧历史为空是预期行为。
- DeepSeek 首输出前才允许重试；超时、上游协议/网络失败均使用不泄密的受控提示。
- 搜索结果被截断、清理控制字符并明确标记为不可信资料，禁止其中指令覆盖系统提示。
- 同一 user+role 使用 Redis token lease 串行生成；PostgreSQL、Redis 或 DeepSeek 故障不得暴露内部详情。

## 验收证据（完成记录提交前复核）

- 自动化覆盖 JWT access/refresh/过期/伪造/算法固定、越权、请求校验、SSE 顺序、模型选择、首 token/总超时边界、首分片后不重试、上游关闭、历史持久/隔离/重启和依赖故障。
- 临时 PostgreSQL 完成 P03 migration upgrade → check → downgrade → upgrade；真实 Redis 覆盖 token lease 的串行与原子释放。
- 实际 Codex 内置浏览器通过旧 Vue 页面验证五个 prompt、普通聊天、深度 reasoning→chat、刷新后历史恢复以及 normal/master 角色隔离。
- 浏览器验收只使用本机隔离 PostgreSQL/Redis、mock Core/DeepSeek 和真实 FastAPI/Vue；全部临时进程与数据已清理，未连接生产服务。
