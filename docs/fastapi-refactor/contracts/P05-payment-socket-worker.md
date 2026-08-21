# P05 支付、Socket.IO 与任务契约

基线：NestJS 支付 controller/service、Socket gateway、AI digest queue/processor 以及 Vue
`Pay.vue`/`userSocket.ts`。HTTP 前缀保持 `/api/v1`；成功 API 保持统一 envelope，支付宝通知按其协议返回纯文本。

## HTTP 路由

| 方法 | 路径 | 身份 | 请求 | 成功响应 | 主要失败 |
|---|---|---|---|---|---|
| POST | `/pay/create` | Bearer access | 旧字段 `subject/body/total_amount/courseId` | envelope data：`payUrl/timeExpire` | 401、404、409、422、503 |
| POST | `/pay/notify` | 支付宝 RSA2 签名 | `application/x-www-form-urlencoded` 原始通知字段 | 精确纯文本 `success` | 纯文本 `failure`，400 或 503 |
| GET | `/pay/status/{outTradeNo}` | Bearer access | 当前用户订单号 | envelope data：`outTradeNo/tradeStatus/isPurchased` | 401、404、422、503 |

`create` 只把三个客户端结算字段作为旧载荷兼容输入；实际课程、标题、说明和金额均从数据库读取。用户身份只取 access token。未过期待支付订单和已购课程返回 409。

通知先以原始非空字段排序并排除 `sign/sign_type` 后做 RSA2/SHA-256 验签，再校验 `app_id`、`seller_id`、订单、金额、支付宝交易号、课程事实和状态迁移。`PaymentRecord`、`CourseRecord` 和唯一 `BackgroundJob` 在同一事务提交；提交后才尝试入队。重复或允许忽略的乱序通知返回 `success`，不会重复权益或事件。未知订单、无效签名、商户/金额/交易号不符和非法状态返回 `failure`。

## Socket.IO

- 连接路径：`/socket.io`，namespace `/`，保持 WebSocket 客户端兼容。
- 身份：`auth.token`（也接受 `Authorization: Bearer ...` 形状）必须是有效 access token。
- 旧 query `userId` 可保留，但必须等于 token 的 `userId`；裸 userId 不能建立连接。
- 房间：服务端只按签名身份加入 `user_{userId}`。
- 支付事件：`paymentSuccess`，载荷保持 userId 字符串。
- 多进程：HTTP 实例和 worker 使用同一 Redis channel；同一用户多连接均接收，其他用户不接收。

前端 P05 仅增加 Socket.IO 握手 token。支付成功后的 API 主动确认和统一重连体验属于 P06。

## 后台任务与恢复

`BackgroundJob.taskKey` 唯一，任务类型为 `PAYMENT_SUCCESS` 或 `EMAIL_DIGEST`，状态为
`PENDING/PROCESSING/COMPLETED/FAILED`。worker 使用数据库行锁和租约抢占，单次超时、指数退避、最大尝试次数及失败错误码均持久化。

- 支付事务创建 `payment:{paymentId}:success`；Socket/Redis 失败不回滚支付或权益。
- 调度器每分钟以 Redis NX 锁扫描到期摘要，创建 `email-digest:{date}:{userId}`。
- 调度器每分钟恢复到期 PENDING 和租约过期 PROCESSING 任务；进程重启不会使数据库任务静默丢失。
- 邮件 Message-ID 使用稳定 job id；已完成任务不会再次执行。SMTP 在结果不明确时仍是至少一次语义，接收方可能按 Message-ID 去重。
- `en-learning-worker-replay` 重放可恢复任务；`--include-failed` 是显式人工补偿，会重置耗尽任务的尝试次数。

## 明确批准的安全差异

1. 客户端金额、标题、body 用户/课程不再作为可信结算事实。
2. 支付回调不再无条件更新记录；必须验签并匹配应用、商户、订单、金额和状态机。
3. Socket.IO 不再信任裸 query `userId`，必须携带 Bearer access token。
4. 新增按当前 JWT 用户隔离的支付状态查询，供即时通知失败后的最终状态恢复。
5. 支付事件和每日摘要从 Web 进程内副作用迁为 PostgreSQL 持久任务加独立 Redis worker/scheduler。

P05 不包含 P06 全链路前端适配、性能容量定案，也不包含 P07 生产 Nginx/systemd、真实支付或切流。
