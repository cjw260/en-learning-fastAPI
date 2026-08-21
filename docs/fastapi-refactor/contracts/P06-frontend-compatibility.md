# P06 前端兼容与安全差异矩阵

状态：`ACCEPTED`

本矩阵锁定 P06 前端在 FastAPI 与 NestJS 回退目标之间的外部契约。路径、HTTP 方法、主要字段、成功 envelope 和实时事件名保持不变；仅记录已经由根计划批准的身份与安全差异。

## 地址与协议

| 面 | 保持的契约 | P06 行为 |
|---|---|---|
| Core HTTP | 同源 `/api/v1` | Axios 集中附加 Bearer；401 共享一次 refresh 后只重放原请求一次 |
| AI HTTP/SSE | 同源 `/ai/v1` | Axios 与 SSE 使用同一 access token/refresh 协调器 |
| Socket.IO | 现有 Socket URL、`/socket.io`、`paymentSuccess` | `auth.token` 是 FastAPI 唯一身份依据；refresh 后原连接以新 token 重连 |
| 静态资源 | `/en/` 基础路径 | Three.js 模型改用 `BASE_URL`，部署子路径不再请求根目录 `/models` |

## 调用方矩阵

| 调用方 | 兼容输入/输出 | P06 约束与失败语义 | 证据 |
|---|---|---|---|
| Core/AI Axios | URL、方法、envelope 不变 | 并发 401 只发送一次 refresh；成功后各自重放；失败时所有等待者 reject 并清空会话，不留下悬挂 Promise | `session.test.ts` 与浏览器支付创建的 401 → refresh 200 → 原请求 200 |
| AI SSE | `{role, content, userId, deepThink, webSearch}` 与 reasoning/chat JSON 帧不变 | 首帧前 401 仅重试一次；首帧后错误不重试；35 秒首帧、130 秒总时限；取消会终止传输且不重复追加 | `stream.test.ts` 九项测试中的 SSE 五项及实际浏览器普通/深度/停止状态 |
| Socket.IO | `paymentSuccess` 事件与 userId 载荷不变 | `auth.token` 必填；旧 NestJS 所需的 query userId 仅作为回退提示同时发送，FastAPI 会校验它必须等于 JWT 用户，绝不把它作为身份来源 | P05 双进程/越权测试；P06 浏览器连接、token refresh 重连与支付事件 |
| 支付创建 | 原请求仍携带旧 `subject/body/total_amount/courseId` | 服务端继续只信任课程事实；响应增加可选 `outTradeNo`，旧响应可从 `payUrl.biz_content.out_trade_no` 解析 | `payment-status.test.ts`、`test_payment_jobs.py`、实际沙箱订单 |
| 支付确认 | `paymentSuccess` 仍可驱动 UI | Socket 只触发状态查询；每 2 秒轮询、重连和手工刷新均查询 `/pay/status/{outTradeNo}`；只有 API 确认 `isPurchased` 后成功。旧 NestJS 404 时仅允许已匹配用户的 Socket 事件回退 | `PaymentStatusPoller` 并发/一次成功测试与浏览器签名回调闭环 |
| Tracker | 原六类埋点载荷不变 | `update-uv` 随当前登录状态携带 Bearer；失败不阻塞页面，SDK 可在后续页面初始化重试 | 浏览器日志中 uv/pv/event/update-uv 均 200 |

## 已批准的安全差异

1. 客户端 userId 不再决定 FastAPI HTTP、SSE 或 Socket 身份；JWT 是唯一可信来源。
2. refresh token 失败会统一登出并拒绝所有等待请求，不再保持旧实现中的悬挂队列。
3. 支付成功 UI 不再仅相信一次实时事件；FastAPI 状态 API 是最终事实。
4. `outTradeNo` 是向后兼容的可选新增字段，不删除或改名任何旧字段。
5. 支付宝沙箱账号与密码不再硬编码或展示；本地验收使用确定性 mock，真实供应商凭据仍只允许来自未提交的环境配置。

## 回退说明

- 同一 P06 前端构建可调用旧 NestJS 的现有 Core/AI 路径；额外 Bearer header 对旧路由无破坏。
- Socket 握手同时保留旧 NestJS query userId，并始终发送新 `auth.token`。FastAPI 对 query 做 JWT 一致性校验，裸 query 连接仍被拒绝。
- 旧 NestJS 没有支付状态查询时，前端将 404 记录为回退能力差异，并只接受该订单用户的旧 `paymentSuccess` 事件；切回 FastAPI 后恢复 API 最终确认。
- AI SSE 的 Bearer 要求属于批准的安全修复；回退到未鉴权旧 AI 时附加 header 不改变旧请求字段或事件载荷。
