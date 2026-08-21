# NestJS 旧系统兼容基线

采集日期：2026-08-21

基线提交：`d406e11`

基线分支：`main`

用途：后续 FastAPI 契约测试和回退比较。此文档描述旧系统事实，不代表所有旧行为都应原样保留；安全例外见根 `AGENTS.md`。

## 1. 进程与入口

| 应用 | NestJS 入口 | 端口 | 全局前缀 | URI 版本 |
|---|---|---:|---|---|
| Core API | `server/apps/server/src/main.ts` | 3000 | `/api` | 默认 `/v1` |
| AI API | `server/apps/ai/src/main.ts` | 3001 | `/ai` | 默认 `/v1` |

两个应用都注册全局成功拦截器和 `HttpException` filter。生产当前由 PM2 cluster 管理，每个应用 4 实例。

## 2. 通用 HTTP 响应

成功响应由拦截器包装：

```json
{
  "timestamp": "ISO-8601",
  "path": "/api/v1/...",
  "message": "Success 或业务消息/请求成功",
  "code": 0,
  "success": true,
  "data": {}
}
```

说明：业务 service 通常先返回 `{data, code: 0, message: "Success"}`，全局拦截器再展开为上述结构；直接返回字符串的健康首页最终 `data` 为 `null`。

`HttpException` 失败响应：

```json
{
  "timestamp": "ISO-8601",
  "path": "/api/v1/...",
  "message": "错误消息",
  "code": 401,
  "success": false
}
```

现有很多业务错误通过 HTTP 200 + `success: true` + 内层 `code: -1` 的方式被拦截器重新包装，语义存在缺陷。FastAPI 迁移应建立契约夹具并按已批准安全/正确性策略修正，前端相应适配。

## 3. Core API 路由

所有路径以下表路径加 `/api/v1`。

| 方法 | 路径 | 认证 | 请求/关键参数 | 主要返回/副作用 |
|---|---|---|---|---|
| GET | `/` | 否 | 无 | 健康/Hello 字符串，经拦截器后 data 为 null |
| POST | `/user/login` | 否 | `phone`, `password` | 用户资料 + access/refresh token；更新 lastLoginAt |
| POST | `/user/register` | 否 | `name`, `phone`, `email?`, `password` | 创建用户并签发 token |
| POST | `/user/refresh-token` | 否 | `refreshToken` | 新 access/refresh token |
| POST | `/user/upload-avatar` | **旧实现无认证** | multipart key `file`，最大 5MB | 上传 MinIO，返回 `previewUrl`, `databaseUrl` |
| POST | `/user/update-user` | Bearer access | 用户可编辑字段 | 更新当前 JWT 用户资料 |
| GET | `/word-book` | 否 | `page`, `pageSize`, `word?`, 八个 tag bool | `{total, list}`；旧实现按字符串 `frq desc` |
| GET | `/course/list` | 否 | 无 | 课程数组，price 为两位小数字符串 |
| GET | `/course/my` | Bearer access | 无 | 当前用户 TRADE_SUCCESS 课程 |
| GET | `/learn/word/:id` | Bearer access | course id | 已购买课程中未学习的 10 个单词 |
| POST | `/learn/word/master` | Bearer access | `{wordIds: string[]}` | 创建学习记录并增加 wordNumber |
| POST | `/pay/create` | Bearer access | `subject`, `body`, `total_amount`, `courseId` | 创建订单并返回 `payUrl`, `timeExpire` |
| ALL | `/pay/notify` | 支付宝回调 | 表单字段 | 更新订单、创建课程记录、Socket.IO 通知，返回 true |
| POST | `/tracker/uv` | 否 | `UvDto` | 创建/读取 Visitor |
| POST | `/tracker/update-uv` | 否 | `visitorId`, `userId` | Visitor 绑定用户 |
| POST | `/tracker/performance` | 否 | Web Vitals 字段 | 写 PerformanceEntry |
| POST | `/tracker/pv` | 否 | `PvDto` | 写 PageView |
| POST | `/tracker/event` | 否 | `EventDto` | 写 TrackEvent |
| POST | `/tracker/error` | 否 | `ErrorDto` | 写 ErrorEntry |

## 4. AI API 路由与 SSE

所有路径以下表路径加 `/ai/v1`。

| 方法 | 路径 | 旧认证 | 请求/参数 | 返回 |
|---|---|---|---|---|
| GET | `/` | 否 | 无 | 健康/Hello |
| GET | `/prompt/list` | 否 | 无 | `{id,label,role}` 数组 |
| POST | `/chat` | **无认证** | `deepThink`, `webSearch`, `role`, `content`, `userId` | SSE 流 |
| GET | `/chat/history` | **无认证** | query `userId`, `role` | 历史消息数组 |

SSE 响应头：

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

每个事件格式：

```text
data: {"content":"...","role":"ai","type":"reasoning"}

data: {"content":"...","role":"ai","type":"chat"}

```

旧实现使用 `${userId}-${role}` 作为 LangGraph thread id；`userId` 来自客户端且未鉴权。迁移必须保留事件形状，但改由已认证身份绑定历史。

## 5. Socket.IO 基线

- 传输：前端强制 `websocket`。
- 连接：前端通过 query `userId`，服务端将连接加入 `user_<userId>` 房间。
- 重连：最多 5 次，延迟 1–5 秒。
- 事件：支付成功后向用户房间发送 `paymentSuccess`，载荷为 userId 字符串。
- 旧风险：握手无认证；单进程内 emit，不具备明确 Redis adapter，PM2 多实例下事件可能无法跨实例到达。

FastAPI 必须使用 JWT 绑定房间并用 Redis 跨进程广播，同时维持客户端事件名和主要载荷兼容。

## 6. 数据模型

Prisma schema 位于 `server/prisma/schema.prisma`，主要模型：

- `User`
- `WordBook`
- `WordBookRecord`，唯一键 `(userId, wordId)`
- `Course`
- `CourseRecord`，唯一键 `(userId, courseId)`
- `PaymentRecord`，`outTradeNo` 唯一
- `Visitor`
- `PageView`
- `TrackEvent`
- `PerformanceEntry`
- `ErrorEntry`

支付状态：`NOT_PAY`、`WAIT_BUYER_PAY`、`TRADE_CLOSED`、`TRADE_SUCCESS`、`TRADE_FINISHED`。

数据库为 PostgreSQL。Prisma 当前迁移：

- `20260404022758_init`
- `20260409080818_add_bio_is_timing_task_timeing_task_time`
- `20260428011939_init_tracker`

## 7. 初始化数据

`server/prisma/seed.ts` 包含八门课程：

| value | 名称 | 图片 |
|---|---|---|
| gk | 高考单词 | `server/prisma/assets/gk.png` |
| zk | 中考单词 | `server/prisma/assets/zk.png` |
| gre | GRE单词 | `server/prisma/assets/gre.png` |
| toefl | 托福词汇 | `server/prisma/assets/toefl.png` |
| ielts | 雅思词汇 | `server/prisma/assets/ielts.png` |
| cet6 | 大学英语六级单词 | `server/prisma/assets/cet6.png` |
| cet4 | 大学英语四级单词 | `server/prisma/assets/cet4.png` |
| ky | 考研单词 | `server/prisma/assets/ky.png` |

旧 seed 会创建 MinIO `course` bucket、设置公开读取策略、上传图片并逐条 `course.create`；它不是幂等的。P02 将改为 upsert 和可审计报告。

WordBook 将使用固定版本 ECDICT 重建。本地没有生产业务数据，用户、学习、支付、埋点和旧 AI 历史不进入开发 seed。

## 8. 外部依赖与环境变量类别

| 依赖 | 用途 | 主要风险 |
|---|---|---|
| PostgreSQL | 业务数据、LangGraph checkpoint | 事务、连接池、迁移竞争 |
| Redis/BullMQ | 每日摘要和邮件任务 | 重复任务、重试、调度锁、多进程 |
| MinIO | 头像、课程图片 | bucket 策略、MIME、对象覆盖、失败清理 |
| DeepSeek/LangChain | 普通/推理模型 | 超时、断连、费用、内容隐私 |
| Bocha Search | AI 联网搜索 | 上游失败、提示注入、来源数据 |
| 支付宝 | 订单支付 | 验签、金额信任、重复/乱序回调 |
| SMTP/Nodemailer | 每日邮件 | 重试、重复发送、隐私 |

真实 `.env` 位于 `server/.env` 且被忽略；任何基线/日志/夹具不得包含值。

## 9. 已确认的高风险旧行为

以下行为不得机械照搬：

1. 密码明文存储和字符串比较。
2. `/user/upload-avatar` 无认证且只检查大小，不校验 MIME/内容。
3. AI chat/history 信任客户端 userId，存在越权风险。
4. Socket.IO query userId 无鉴权。
5. 支付创建信任客户端金额/标题，notify 未见验签、金额/商户校验。
6. notify 在数据库事务提交前发送 Socket.IO，实时通知不是可靠交付。
7. `saveWordMaster` 对重复 wordIds 和并发缺乏幂等处理，计数可能漂移。
8. WordBook `frq` 为字符串并按 `desc` 排序，与目标数值升序不符。
9. HTTP 业务错误与真实状态码/`success` 语义可能不一致。
10. AI 和 Core controller 大多仅依赖 TypeScript 类型，缺少运行时 DTO 校验。
11. PM2 多实例下 Socket.IO 未见 Redis adapter 配置。
12. 每个 AI 进程启动时都注册重复定时任务的风险。

## 10. 前端调用基线

- Axios Core：`baseURL: /api/v1`，Bearer access token，超时 50 秒。
- Axios AI：`baseURL: /ai/v1`，当前未自动携带 token。
- SSE：`/ai/v1/chat`，`fetch-event-source`，JSON body，当前未携带 token。
- Socket.IO：URL 来自 `VITE_SOCKET_URL`，当前 query userId。
- MinIO 图片：基础 URL 来自 `VITE_MINIO_ENDPOINT`。
- refresh token 使用独立 Axios 客户端，避免拦截器递归；旧并发失败路径可能留下未 reject 的等待请求。

## 11. 构建、测试与部署基线

- 本地版本：Node `v24.18.0`、pnpm `10.32.1`。
- 2026-08-21 执行 `pnpm --dir server exec nest build server`：失败，`Command "nest" not found`，说明当前工作区依赖未安装。
- 仓库没有 `*.spec.ts`、`*.test.ts` 或 E2E 测试文件。
- 仓库没有 `.github/workflows`。
- 当前部署脚本构建 tracker、NestJS server、NestJS ai、Vue web，随后 PM2 删除全部进程并以 cluster 模式启动两服务。
- 当前机器没有数据库业务数据，因此 P00 不执行运行时 API 基线请求；静态契约作为初始基线，后续用夹具和可控临时依赖补足。
