# P03：AI 服务迁移

状态：`NOT_STARTED`

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

- [ ] `/ai/v1` 路径、方法、prompt/chat/history schema 兼容。
- [ ] reasoning/chat 分片、顺序、结束和 header 正确。
- [ ] 断连、超时、上游失败、无效角色和超长输入受控。
- [ ] AI 身份不可由 body/query userId 越权伪造。
- [ ] 新历史持久、隔离、重启可恢复；旧历史为空已记录。
- [ ] 日志不含密钥或完整敏感对话。
- [ ] 前端普通/深度思考/历史浏览器验证通过。
- [ ] 未实现 Core 业务、支付、Socket.IO 或 worker。

## 回退

将 Nginx `/ai/` upstream 指回 NestJS :3001；新历史表独立保留。
