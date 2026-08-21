# FastAPI 重构进度

最后更新：2026-08-21

## 当前执行锁

| 字段 | 值 |
|---|---|
| Active phase | `P06`：前端适配与全链路验收（已完成） |
| Phase status | `COMPLETED` |
| Phase lock | `P06 ONLY`（仅完成记录；不得在本次执行中启动 P07） |
| Allowed scope | P06 完成记录、提交与推送；禁止新增运行时实现 |
| Forbidden scope | P07 生产部署、数据库切换、Nginx/systemd/PM2、真实支付、生产凭证/数据与旧服务处置 |
| Required skill | `en-learning-backend-refactor` |
| Skill status | `LOADED` |
| Skill loaded at | 2026-08-21（P06 当前执行重新加载） |
| Next phase | `P07`，仅在 P06 全部验收、审查、复测、提交和推送完成后，由用户在新的执行中明确启动 |

## 阶段状态

| 阶段 | 状态 | 完成提交 | 备注 |
|---|---|---|---|
| P00 仓库、计划与基线 | `COMPLETED` | `984d60e` | 主提交已推送到新 origin 的阶段分支 |
| P01 工程骨架与数据库基础 | `COMPLETED` | `bb0a24b` | 主提交已推送到 `origin/codex/p01-fastapi-foundation` |
| P02 数据初始化 | `COMPLETED` | `8c5bf25` | 主提交已推送到 `origin/codex/p02-data-bootstrap` |
| P03 AI 服务 | `COMPLETED` | `fc0e503` | 主提交已推送到 `origin/codex/p03-ai-service` |
| P04 核心业务 API | `COMPLETED` | `b51f41b` | 主提交已推送到 `origin/codex/p04-core-api` |
| P05 支付/Socket.IO/worker | `COMPLETED` | `d9ed248` | 主提交已推送到 `origin/codex/p05-payment-socket-worker` |
| P06 前端与全链路验收 | `COMPLETED` | `4c912aa` | 主提交已推送到 `origin/codex/p06-frontend-verification` |
| P07 灰度上线与清理 | `NOT_STARTED` | — | — |

## P06 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求进行下一个阶段 | PASS |
| 必需 skill | 本次从仓库完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 根目录与四项标识全部存在 | PASS |
| P05 前置条件 | `d9ed248` 主提交与 `fe6f051` 完成记录已推送 | PASS |
| 启动分支 | 从已完成 P05 创建 `codex/p06-frontend-verification` | PASS |
| 启动工作区 | 无已修改/已暂存文件；仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 调用方基线 | 已重读 Axios refresh、AI SSE、Socket、支付弹窗、tracker、登录/资料/课程/学习/词库/聊天调用方 | PASS |
| 技术映射 | 已完整读取 `framework-parity.md`，锁定真实 HTTP/SSE/Socket 运行时契约、多进程与资源观察边界 | PASS |
| 视觉门禁 | 1440 × 900 保存并复验主页、登录、支付、课程、词库、学习与 AI；保持既有布局，仅补加载/空/错误/取消/最终确认状态 | PASS |

## P06 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P06 | 阶段锁、最终 diff 与生产改动扫描 | 仅前端安全适配、可选支付响应字段、测试/验收脚本与 P06 文档；未改 server、部署或生产 | PASS |
| Web 构建、类型与新增自动化 | `pnpm` type-check/build/test | Web `9 passed`；tracker type-check PASS；Web 顺序 type-check + tracker build + Vite production build PASS | PASS |
| 关键用户旅程及状态 | 隔离本地服务与实际浏览器同视口验收 | 注册/错误登录/恢复、资料头像、8 课程、签名支付、10 词学习、15 词分页、AI 普通/深度/历史/取消、tracker 全部通过 | PASS |
| 契约差异受控 | NestJS/FastAPI 夹具、旧调用方与批准差异清单 | `contracts/P06-frontend-compatibility.md` 锁定路径、字段、envelope、SSE、Socket、支付与回退差异 | PASS |
| refresh/SSE/Socket 无悬挂或重复 | 并发刷新、失败清队列、取消/超时/401、重连/多事件测试 | 共享一次 refresh；失败统一 reject；SSE 五类自动化及浏览器停止；Socket 新 token 重连且 FastAPI 只信 JWT | PASS |
| 支付 API 最终确认 | Socket 事件、轮询/重连与状态 API 测试 | Poller 合并并发查询且 success 一次；浏览器回调后由状态 API 确认并切换我的课程 | PASS |
| 性能与资源基线 | 关键 API 并发冒烟、延迟统计、数据库池/Redis/FD 重复观察 | 每端点 200 请求/并发 20/0 错误/P95 < 500 ms；PG `6→8→8`、Redis `9→9→9`、Core FD `89→91→91` | PASS |
| P07 清单完整且未改生产 | 验收报告、配置建议、回退与生产范围扫描 | `P06-ACCEPTANCE.md` 含容量起点、风险和 P07 只读清单；未连接或修改生产 | PASS |

## P05 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求进行下一阶段 | PASS |
| 必需 skill | 本次从仓库完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 根目录与四项标识全部存在 | PASS |
| P04 前置条件 | `b51f41b` 主提交与 `2da6c4b` 完成记录已推送 | PASS |
| 启动分支 | 从已完成 P04 创建 `codex/p05-payment-socket-worker` | PASS |
| 启动工作区 | 仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 旧系统基线 | 已重读 pay controller/service、Socket gateway、digest queue/processor、邮件服务和 Vue 支付/Socket 调用 | PASS |
| 技术映射 | 已完整读取 `framework-parity.md`，锁定验签原始字段、事务后副作用、JWT 房间、Redis 多进程和独立 worker 边界 | PASS |
| 视觉门禁 | N/A（后端高风险集成）；以 HTTP/Socket/worker 协议、双进程、故障注入、前端类型和构建验收 | N/A |

## P05 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P05 | 阶段锁、OpenAPI/模块和最终 diff 范围检查 | 仅支付、Socket.IO、worker/调度、握手 token、迁移、测试与文档；无 P06/P07 运行时 | PASS |
| 服务端可信结算事实 | 伪造金额/标题/用户、订单并发和购买权测试 | 只以 JWT 当前用户与 Course 数据生成订单；待支付/已购冲突受控 | PASS |
| 支付宝通知安全与幂等 | RSA2、商户、金额、未知订单、重复/乱序/并发测试 | 原始字段验签后校验 app/seller/order/amount/tradeNo；同订单行锁与状态机通过 | PASS |
| 权益与可靠事件同事务 | PostgreSQL 事务、唯一键和入队失败注入 | PaymentRecord/CourseRecord/BackgroundJob 单事务；入队失败后状态 API 仍显示已购且任务可恢复 | PASS |
| Socket.IO 身份与多实例 | 两个 Uvicorn、真实 Redis、三用户连接和重连测试 | JWT 决定 `user_{id}`；同用户跨实例/多连接收到 `paymentSuccess`，他人/裸 userId 被拒绝 | PASS |
| worker 重启与重复投递 | 并发 claim、租约、恢复扫描、人工 replay 测试 | 数据库状态机只完成一次；到期/租约过期任务每分钟恢复；耗尽任务可显式补偿 | PASS |
| 摘要调度和邮件故障 | Redis NX 锁、日期唯一键、SMTP 故障和重试测试 | 同日同用户只建一项；重启可执行；失败持久化并按稳定 Message-ID 重试 | PASS |
| 依赖故障不破坏支付事实 | Redis/Socket/SMTP/即时入队故障注入 | 支付与权益先提交；通知失败只影响 durable job，API 查询和 replay 可最终一致 | PASS |
| 敏感日志与配置 | 结构化日志、SecretStr、测试日志和敏感模式扫描 | 日志仅哈希引用/任务类型/失败类别；不记录签名、订单全文、邮件正文或凭证 | PASS |
| 自动化与构建 | uv/Ruff/mypy/pytest/Vue type-check/build | uv 锁文件可离线检查；Ruff/mypy 通过；pytest `81 passed`；前端 type-check/build 通过 | PASS |

## P04 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求继续下一阶段 | PASS |
| 必需 skill | 本次从仓库完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 根目录与四项标识全部存在 | PASS |
| P03 前置条件 | `fc0e503` 主提交与 `eb407cb` 完成记录已推送 | PASS |
| 启动分支 | 从已完成 P03 创建 `codex/p04-core-api` | PASS |
| 启动工作区 | 仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 技术映射 | 已完整读取 `framework-parity.md`，锁定 Depends/session、JWT、multipart、事务和异步 MinIO 边界 | PASS |
| 视觉门禁 | N/A（纯后端）；以路径、schema、状态码、错误 envelope、OpenAPI 和前端核心流程验收 | N/A |

## P04 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P04 | 阶段锁、OpenAPI/模块与最终 diff 范围检查 | 仅用户/头像/课程/词库/学习/tracker、迁移、测试和文档；无 P05+ 路由或运行时 | PASS |
| 全部既有 Core 非支付路由契约 | NestJS/前端清单、HTTP/OpenAPI 与自动化夹具 | 16 条既有非支付路由逐项清单、OpenAPI 与成功/失败集成测试通过 | PASS |
| envelope、状态码及序列化兼容 | 成功/错误、date/Decimal/null 契约测试 | 统一 envelope、真实 4xx/5xx、UTC Z、两位价格、null 及前端实际载荷通过 | PASS |
| 密码与 JWT 安全 | 哈希、access/refresh、过期/伪造/越权测试 | versioned scrypt、旧值升级、token 类型/过期/签名、refresh 行锁轮换与重放测试通过 | PASS |
| 头像上传安全 | 认证、内容/MIME/大小/对象覆盖/失败清理测试 | Bearer、PNG/JPEG/WebP magic/后缀、5 MiB、随机用户对象键、清理及真实 MinIO 浏览器上传通过 | PASS |
| WordBook 查询正确 | 过滤、分页、ECDICT 标签与稳定 `frq` 排序测试 | 八标签、空搜索兼容、分页和 `frqRank → word → id` 稳定顺序自动化/浏览器通过 | PASS |
| 学习事务与并发正确 | 购买权、重复/并发掌握、wordNumber 测试 | 支付成功课程权限、课程词归属、PostgreSQL upsert、重复/并发计数及浏览器 10 词流程通过 | PASS |
| 埋点边界与隐私 | schema、超大载荷、速率、依赖错误、日志秘密测试 | 64 KiB、Redis 限速、访客防重绑、敏感 key/text/URL 清洗和依赖故障测试通过 | PASS |
| 未实现 P05+ | 范围扫描和最终 diff 审查 | 支付创建/回调、Socket.IO、worker、Nginx/生产部署均未实现 | PASS |

## P03 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求进行下一阶段 | PASS |
| 必需 skill | 本次完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 根目录与四项标识全部存在 | PASS |
| P02 前置条件 | `8c5bf25` 主提交与 `4b82d7f` 完成记录已推送 | PASS |
| 启动分支 | 从已完成 P02 创建 `codex/p03-ai-service` | PASS |
| 启动工作区 | 仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 旧系统基线 | 已重读 prompt/chat/history、JWT claims、DeepSeek/Bocha、LangGraph checkpoint、SSE 和前端调用 | PASS |
| 技术映射 | 已完整读取 `framework-parity.md`，锁定 ASGI 流、请求级事务、显式 LLM/搜索适配和多进程 Redis 边界 | PASS |
| 视觉门禁 | N/A（纯后端）；以路径、schema、SSE headers/事件、OpenAPI、前端实际浏览器状态验收 | N/A |

## P03 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P03 | 阶段锁、OpenAPI/模块与最终 diff 范围检查 | 仅 AI 路由/认证/适配/历史、必要前端 Bearer、测试和文档；OpenAPI 无 P04+ | PASS |
| prompt/chat/history 契约兼容 | HTTP/OpenAPI/前端类型与旧 NestJS 夹具对照 | 五角色顺序、路径/方法、chat 字段、history 数组及成功 envelope 自动化通过 | PASS |
| SSE 分片、顺序、结束与 headers | mock LLM 流式集成测试 | reasoning→chat、同 chunk 拆分逻辑、自然结束、heartbeat 注释、no-transform/no-buffer headers 通过 | PASS |
| 断连、超时和上游错误受控 | 取消/超时/DeepSeek 故障注入 | consumer close 关闭上游；首 token/总超时受控；首分片后不重试；错误为通用 SSE | PASS |
| JWT 身份与越权保护 | access/refresh/伪造/mismatch 测试 | HS256 固定、签名/exp/nbf/access 校验；body/query userId 不一致为 403 | PASS |
| 历史持久、隔离和重启恢复 | 临时 PostgreSQL 迁移与跨应用读取测试 | 新表 migration 往返/check；user+role 隔离；重启恢复；旧历史初始空数组 | PASS |
| PostgreSQL/Redis/DeepSeek 故障安全 | 依赖故障与日志秘密扫描 | PostgreSQL/Redis/DeepSeek 故障注入通过；Redis 原子 lease 实测；JSON 日志仅白名单元数据 | PASS |
| 前端普通/深度思考/历史体验 | 实际浏览器验证 | 旧 Vue 页五角色、普通、深度 reasoning→chat、刷新恢复、normal/master 隔离全部通过 | PASS |

## P02 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求进行下一阶段 | PASS |
| 必需 skill | 本次完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 根目录与四项标识全部存在 | PASS |
| P01 前置条件 | `bb0a24b` 主提交与 `cf15548` 完成记录已推送 | PASS |
| 启动分支 | 从已完成 P01 创建 `codex/p02-data-bootstrap` | PASS |
| 启动工作区 | 仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 旧系统基线 | 已重读 Prisma `WordBook`/`Course`、`seed.ts`、八张 PNG、MinIO 规则和前端字段 | PASS |
| 技术映射 | 已重读 `framework-parity.md` 的数据、事务、异步文件/MinIO 条目 | PASS |
| 视觉门禁 | N/A（纯后端）；以单命令、数据约束、对象 HEAD、报告和失败契约验收 | N/A |
| 固定来源 | ECDICT `1.0.28` / `8defb761...` / 65,936,699 bytes / SHA-256 `d0ce61e5...` / MIT | PASS |

## P02 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P02 | 阶段锁、路由/模块与 diff 范围检查 | 仅数据迁移、bootstrap、测试、来源/许可和 P02 文档；无 P03+ API/业务/部署 | PASS |
| 空库一条命令初始化 | 临时 PostgreSQL/MinIO 调用 CLI | `en-learning-bootstrap` 完成 migrate → 770,611 词 → 8 课程 → 8 图片 → verify/report | PASS |
| 来源、许可和校验可追溯 | 固定清单、运行前大小/SHA 校验、许可文件测试 | tag/commit/URL/65,936,699 bytes/SHA-256/MIT 全部记录并自动核对 | PASS |
| 连续两次幂等 | 同一隔离环境连续执行两次完整 CLI | 第二次 770,611 词、8 课程、8 对象全部 skip；总量不变 | PASS |
| 字段、坏行、批次恢复 | 规范化、拒绝 JSONL、故障注入和重跑集成测试 | BOM/空值/tag/frq/坏行覆盖；第二批失败保留第一批，重跑恢复 | PASS |
| 八课程/八图片完整 | Prisma seed 对照、MinIO stat 与匿名 HEAD | `gk/zk/gre/toefl/ielts/cet6/cet4/ky` 均为 `image/png`、公开 200 | PASS |
| `frq` 稳定排序 | 边界数据 PostgreSQL 查询测试 | 正整数数值升序；null/空/非数值/0 的 rank 为 null，按 word/id 稳定置后 | PASS |
| 不伪造业务数据 | 运行前后保护表计数比较 | 用户、学习、支付、课程记录、访客及四类埋点两次均保持 0 | PASS |
| 失败非零且报告准确 | CLI 故障注入、秘密扫描、生产保护测试 | 失败返回 1、status=failed、无凭证；生产环境在迁移前拒绝 | PASS |
| 自动化与质量门禁 | pytest、Ruff、mypy、uv lock、Alembic check | `40 passed`；Ruff format/lint、mypy、uv lock、Alembic 往返/check、CLI 入口均通过 | PASS |

## P00 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 仓库根目录 | `/Users/woofeel/Downloads/en-learning` | PASS |
| 必需标识 | `server/nest-cli.json`、`server/package.json`、`apps/web`、`packages/common` 全部存在 | PASS |
| 当前分支 | `main`，基线 commit `d406e11` | PASS |
| 原远端 | 已保留为 `nest-origin -> https://github.com/cjw260/en-learning.git` | PASS |
| 新远端 | `origin -> https://github.com/cjw260/en-learning-fastAPI.git` | PASS |
| 需保护的既有未跟踪内容 | `.agents/`、`.codex/`；不得作为 P00 顺带提交 | PASS |
| 根计划 | 原 `AGENTS.md` 只有部署备忘；用户已授权升级为权威计划 | PASS |
| 旧系统测试 | 无测试文件、无 CI | RECORDED GAP |
| 本地旧系统构建 | `nest` 命令不存在，因为工作区依赖未安装 | RECORDED GAP |
| 本地数据库 | 没有业务数据，不运行生产数据导出/复制 | EXPECTED |

## P01 启动基线

| 检查 | 证据 | 状态 |
|---|---|---|
| 用户授权 | 用户在 2026-08-21 新执行中明确要求进行下一个阶段 | PASS |
| 必需 skill | 本次完整读取 `en-learning-backend-refactor` | PASS |
| 仓库标识 | 四项标识全部存在 | PASS |
| P00 前置条件 | 完成提交 `984d60e` 与记录提交 `3dfb9af` 已推送 | PASS |
| 启动分支 | 从 `3dfb9af` 创建 `codex/p01-fastapi-foundation` | PASS |
| 启动工作区 | 仅 `.agents/`、`.codex/` 为既有未跟踪内容，继续保护且不提交 | PASS |
| 旧系统基线 | 已重读双入口、响应拦截器/异常过滤器、Prisma schema、Redis/BullMQ 与 MinIO 生命周期 | PASS |
| 技术映射 | 已重读 `framework-parity.md` | PASS |
| 视觉门禁 | N/A（纯后端）；以路径、schema、状态码、错误 envelope、OpenAPI 与模块边界验收 | N/A |
| 本地工具链 | 用户手动安装并核验 Python 3.12.14、uv 0.12.5、PostgreSQL 17.11、Redis 8.10.1 | PASS |

## P01 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 本次只执行 P01 | diff 与路由/模块清单检查 | 仅 `fastapi-backend/` 和 P01 计划/决策/进度文件；无 P02+ 路由、导入或业务实现 | PASS |
| 三类进程启动/停止/资源释放 | 子进程信号测试与生命周期替身 | Core API、AI API、Taskiq worker 均独立启动并完成信号关闭；worker 创建 Redis Stream 消费组；无资源关闭错误 | PASS |
| live/ready 正常与异常语义 | HTTP 契约测试、依赖故障替身 | 正常/故障/超时契约测试通过 | PASS |
| 统一响应与验证错误 | FastAPI HTTP 契约测试 | 成功、404、422、500、request ID 与路径契约通过 | PASS |
| Alembic 往返 | 临时 PostgreSQL upgrade → downgrade → upgrade | PostgreSQL 17 隔离空库完成 upgrade → check → downgrade base → upgrade | PASS |
| ORM 与批准 schema 一致 | SQLAlchemy metadata/迁移/Prisma 对照测试 | 11 表全部列/可空性/主键/关系/索引/唯一键/外键及 Decimal/DateTime/JSONB/枚举测试通过；Alembic check 无漂移 | PASS |
| 配置/日志安全 | 缺失配置与日志捕获测试 | 缺失配置快速失败、错误隐藏输入、日志 request ID/无秘密测试通过 | PASS |
| 质量门禁 | pytest、Ruff format/lint、mypy | uv lock 离线检查通过；Ruff format/lint、mypy 通过；pytest `25 passed` | PASS |
| 无后续阶段功能 | 目录、路由和最终 diff 审查 | OpenAPI 仅 Core/AI 根路由和 live/ready；范围扫描与最终自审通过 | PASS |

## P00 验收清单

| 标准 | 验证方法 | 当前证据 | 状态 |
|---|---|---|---|
| 当前任务加载必需 skill | 完整读取 skill 并记录时间 | 已于 2026-08-21 当前任务读取 | PASS |
| 四个仓库标识存在 | `test -e`/目录检查 | 四项均 OK | PASS |
| 根计划包含阶段/范围/验收 | 阅读 `AGENTS.md` | 已写入权威计划、P00-P07 和硬门禁 | PASS |
| 每阶段有步骤/验收/测试/回退 | 文档结构检查 | 根计划及八个阶段文件均已包含 | PASS |
| 旧系统基线完整 | 对照 controller/service/schema/frontend/deploy | `LEGACY_BASELINE.md` 已覆盖全部类别 | PASS |
| 新对话可恢复状态 | 交叉检查 README/PROGRESS/阶段文件 | 必读顺序、当前锁、最后动作和下一动作完整 | PASS |
| 新旧远端安全配置 | `git remote -v`、`git ls-remote` | `nest-origin` 为旧仓库，`origin` 为新仓库 | PASS |
| 新仓库继承历史 | 比较本地/new origin main commit | 两个远端 `main` 均为 `d406e118ede2fb25ca14b4e95443a2f8dbdb7977` | PASS |
| 文档质量检查 | 链接、`git diff --check`、敏感模式 | 13 个文件存在；空白/冲突/常见密钥检查通过 | PASS |
| 只含 P00 范围 | 最终 diff/status | 仅暂存 `AGENTS.md` 与 `docs/fastapi-refactor/**`；P01 目录不存在 | PASS |
| 阶段提交与推送 | commit/remote branch 检查 | `984d60e` 已推送到 `origin/codex/p00-repository-baseline` | PASS |

## 已完成动作

1. 完整加载 `en-learning-backend-refactor` skill。
2. 验证仓库根目录和四个适用标识。
3. 检查 Git 分支、工作区、远端和最近提交。
4. 静态盘点 NestJS Core/AI 路由、响应、认证、Prisma、Seed、SSE、Socket.IO、BullMQ、外部服务和前端调用。
5. 尝试旧 Core 构建并如实记录依赖未安装导致的失败。
6. 将根 `AGENTS.md` 更新为唯一权威计划并保留部署备忘。
7. 建立文档入口、决策记录、旧系统基线和本进度台账。
8. 将旧远端安全改名为 `nest-origin`，设置新 FastAPI 仓库为 `origin`。
9. 将原始 `main` 推送到新仓库并核验新旧远端 main 均为 `d406e118ede2fb25ca14b4e95443a2f8dbdb7977`。
10. 完成 13 个阶段文档的路径、空白、冲突标记、常见密钥和暂存范围检查。

## 当前阻塞

无 P06 阻塞。实现、自动化、实际浏览器、契约、并发/资源、生产构建、staged diff/敏感信息/范围审查和主提交推送均通过。

## 准确下一动作

结束本次执行，不启动 P07。用户在新的执行中明确授权 P07 后，必须重新加载 `en-learning-backend-refactor`，重读根计划、进度和 P07 文档，并额外确认生产部署授权。

## P06 已完成动作

1. 使用一个共享 refresh 协调器统一 Core Axios、AI Axios 与 SSE：并发 401 只刷新一次，成功后各自重放一次，失败时全部 reject 并统一清空会话。
2. SSE 增加 Bearer、首帧前一次 401 refresh、35 秒首帧/130 秒总时限、显式取消、首帧后故障不重试和定向 assistant 累加，避免重复与悬挂。
3. Socket.IO 以 `auth.token` 为 FastAPI 身份来源，token 变化时同一客户端重连；同时保留旧 NestJS query 作为回退提示，FastAPI 强制与 JWT 用户一致。
4. 支付弹窗对 Socket、重连、2 秒轮询和手工操作统一执行状态 API 最终确认；并发查询合并、成功只发布一次，旧响应可从 Alipay URL 解析订单号。
5. Tracker `update-uv` 携带 Bearer，初始化失败可重试；清理类型错误、未处理 Promise、阻塞式 LCP 和调试日志，并把 tracker 类型检查/声明构建纳入 Web 构建门禁。
6. 为登录、注册、资料头像、课程、词库、学习、聊天补充 loading/empty/error/submit 状态；修复 `/en/` 3D 模型资源路径及动画、controls、renderer、geometry/material 生命周期。
7. 实际浏览器在 1440 × 900 完成注册/错误登录/恢复、资料头像、8 课程、签名支付/Socket/API 最终确认、10 词学习、15 词分页、AI 普通/深度/角色历史/停止和 tracker。
8. 浏览器恰逢 access token 过期，Core 日志证明支付创建 401 → 唯一 refresh 200 → 原请求 200；签名回调、状态查询、我的课程和 wordNumber=10 全部闭环。
9. 本机每端点 200 请求、并发 20 的两轮冒烟均 0 错误且稳定轮 P95 < 500 ms；PG 连接 `6→8→8`、Redis clients `9→9→9`、Core FD `89→91→91`，未见持续增长。
10. 新增 P06 兼容矩阵、验收报告、容量起点与 P07 只读清单；最终 Web `9 passed`、Python `81 passed`，uv/Ruff/mypy/tracker type-check/Web production build 全部通过。

## P06 阶段结束记录

```text
Completed at: 2026-08-21 23:15 CST
Review result: PASS；兼容、认证/refresh、SSE 取消/超时、Socket 身份/重连、支付最终确认、tracker、浏览器全旅程、资源释放、并发/延迟、日志秘密、生产构建和 P06 范围无剩余阻塞问题
Verification commands: UV_CACHE_DIR=/private/tmp/en-learning-p06-uv-cache uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（81 passed）；pnpm --filter @en/web test（9 passed）；pnpm --filter @en/tracker type-check；pnpm --filter @en/web build；实际浏览器注册/登录/资料/头像/课程/支付/学习/词库/AI/tracker；两轮 200 请求/并发 20 冒烟；git diff --cached --check；敏感/生产范围扫描
Commit: 4c912aa (P06 主提交)
Branch: codex/p06-frontend-verification
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P06 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: 本阶段使用生成 RSA、确定性 LLM/支付宝/邮件替身与本机短时并发，不代表真实供应商、生产峰值或长期 soak；Three.js vendor chunk 约 789 kB（gzip 约 205 kB）仍有构建警告。生产备份、真实小额支付、Nginx/systemd、灰度指标、回退演练、旧 PM2/仓库处置均未触碰，必须在新执行获得 P07 明确授权
Next phase start condition: 用户在新的执行中明确启动 P07，重新加载必需 skill，并明确授权生产部署
```

## P05 已完成动作

1. 支付创建保持旧 Vue 请求/响应形状，但用户只取 JWT，课程标题、说明和金额只取数据库；用户行锁阻止并发重复待支付订单。
2. 自建最小 RSA2 适配层，对支付宝原始非空参数排序签名/验签；回调校验 app、seller、订单、金额、tradeNo、课程事实和受控状态机。
3. 在同一 PostgreSQL 事务内更新支付、课程权益与唯一 durable job；并发/重复/乱序通知不会重复授予权益或创建事件。
4. 新增当前 JWT 用户隔离的支付状态查询；即时 Redis/Taskiq 入队失败不会回滚支付事实，可经查询与恢复扫描最终一致。
5. 使用 `python-socketio` 提供 `/socket.io`，由 access token 决定 `user_{id}` 房间；旧 query userId 只能与签名身份一致，事件名/载荷保持 `paymentSuccess`/userId。
6. Redis manager 支持多 Uvicorn 和 worker 跨进程广播；真实双实例、多连接、其他用户隔离、拒绝裸 userId 和重连测试通过。
7. 新增 `BackgroundJob` 行锁/租约状态机、超时、指数退避、最大尝试、错误码、每分钟自动恢复和显式 `en-learning-worker-replay` 补偿入口。
8. 每日摘要以 Redis NX 扫描锁和 `date+user` 唯一键调度；SMTP 放入线程、TLS/SSL 可配置、Message-ID 稳定，重启/重复投递/SMTP 故障测试通过。
9. 前端 Socket.IO 握手增加 access token；P05 契约、配置模板、运行/恢复说明及 P06 边界均已记录，未实施生产部署或 P06 全链路适配。
10. 最终 `81 passed`；uv 锁文件离线检查、Ruff format/lint、mypy、Vue type-check/build、staged diff、敏感信息和范围检查全部通过。

## P05 阶段结束记录

```text
Completed at: 2026-08-21 17:02 CST
Review result: PASS；兼容、验签、可信事实、事务、幂等、状态机、Socket 身份/多进程、worker 恢复、邮件故障、资源释放、日志秘密、测试覆盖和 P05 范围无剩余阻塞问题
Verification commands: UV_CACHE_DIR=/private/tmp/en-learning-uv-cache uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（81 passed，含 Alembic 往返/check、真实 PostgreSQL/Redis/MinIO、双 Uvicorn Socket.IO）；pnpm --filter @en/web type-check；pnpm --filter @en/web build-only；git diff --cached --check；敏感/范围扫描
Commit: d9ed248 (P05 主提交)
Branch: codex/p05-payment-socket-worker
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P05 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: 确定性测试使用生成的 RSA 密钥和假 SMTP，未接触真实支付宝/邮箱凭证、配额或生产网络；SMTP 在服务端已接收但客户端超时的模糊失败下仍可能重复投递，稳定 Message-ID 可供接收方去重。P06 仍需增加支付弹窗主动状态确认、refresh 后 Socket auth 更新和完整浏览器 E2E。生产数据库迁移、真实支付、Nginx/systemd、双服务切换和部署均未触碰
Next phase start condition: 用户在新执行中明确启动 P06，并重新加载必需 skill
```

## P04 已完成动作

1. 迁移 16 条既有非支付 Core API，保持 `/api/v1`、主要请求字段、成功 envelope、课程/单词/用户返回形状和旧前端调用路径。
2. 新注册值使用随机盐 versioned scrypt；旧明文/前端 MD5 值首次登录后升级；access/refresh 类型、过期、签名和 refresh version 轮换受控。
3. 头像上传改为 Bearer 当前用户，校验 multipart 单文件、大小、MIME/扩展名/magic，并使用 `users/{jwt-user}/{uuid}.{ext}` 对象键和失败清理。
4. 课程与 WordBook 保持 Decimal/null/date 兼容，使用内部 `frqRank`、word、id 稳定排序；浏览器发现并修复 `word=` 空查询兼容。
5. 学习接口校验支付成功课程与单词归属，以 PostgreSQL upsert 和原子增量保证重复/并发掌握不重复计数。
6. 六类 tracker 路由增加 64 KiB body 限制、Redis 固定窗口限速、访客防重绑、JWT 身份匹配、敏感 key/text/URL 清洗和通用依赖错误。
7. 浏览器发现并修复资料页会展开完整登录响应的旧运行时载荷；更新 DTO 仅忽略额外只读字段，所有可写字段仍由白名单和 JWT 当前用户决定。
8. 新增可逆 `refreshTokenVersion` 迁移、P04 路由契约清单、真实 PostgreSQL/Redis/MinIO 集成测试、上传/事务/并发/故障/隐私测试和本地浏览器 seed。
9. 实际内置浏览器完成注册、登录、refresh、八课程、已购课程、15 词检索分页、10 词学习/掌握计数、头像上传和资料保存；修复后空搜索与完整资料载荷均复验 200。
10. 最终 `71 passed`；uv lock、Ruff format/lint、mypy、前端 type-check/build、diff/sensitive/scope 检查通过；所有本地临时服务和端口已清理。

## P04 阶段结束记录

```text
Completed at: 2026-08-21 16:02 CST
Review result: PASS；兼容、认证、密码、上传、事务、并发、限速、隐私、依赖故障、浏览器体验、测试覆盖和 P04 范围无剩余阻塞问题
Verification commands: uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（71 passed）；pnpm --filter @en/web type-check；pnpm --filter @en/web build-only；实际浏览器注册/登录/refresh/课程/词库/学习/上传/资料；git diff --cached --check；敏感/范围扫描
Commit: b51f41b (P04 主提交)
Branch: codex/p04-core-api
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P04 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: `tracker/update-uv` 现按安全决策要求 Bearer，但旧 tracker SDK 尚不携带 token，登录后该绑定请求会返回预期 401；P06 必须补 token 并统一前端 4xx/5xx 错误展示。前端构建仍有既有 package type/plugin timing/大 chunk 警告，不影响 P04。真实生产凭证、生产数据、Nginx 切流和部署均未触碰
Next phase start condition: 用户在新执行中明确启动 P05，并重新加载必需 skill
```

## P03 已完成动作

1. 迁移五个旧 prompt mode，保持 `/ai/v1/prompt/list` 顺序、字段与成功 envelope。
2. 实现 legacy-compatible HS256 access token 校验，由 JWT 决定用户，保留但不信任 body/query `userId`。
3. 实现 DeepSeek 普通/推理流式适配、Bocha 有界不可信搜索上下文、连接/首 token/总时长和首输出前有限重试。
4. 使用 `StreamingResponse` 输出旧 reasoning/chat data 帧，增加注释心跳、禁缓冲 headers、断连取消和通用错误提示。
5. 新增 `AIChatThread`/`AIChatMessage` 可逆迁移，按 user+role 隔离、position 排序并支持重启恢复；旧 LangGraph 历史不迁移。
6. 使用 Redis token lease 串行同一 user+role 生成，原子 compare-delete 释放；依赖不可用时安全失败。
7. 前端 AI Axios 和 fetch-event-source 补充 Bearer access token，保留现有页面和业务字段。
8. JSON 日志只输出哈希用户引用、角色、功能开关、分片/字符、token 用量、延迟和失败类型，不输出提示词、令牌、密钥或上游正文。
9. 自动化最终 `58 passed`；uv lock、Ruff format/lint、mypy、Alembic 往返/check、真实 Redis、Web type-check/build 全部通过。
10. 实际 Codex 内置浏览器使用本机隔离服务验证普通/深度聊天、五角色、刷新恢复和角色隔离；临时服务、数据库、Redis 与构建报告均已清理。

## P03 阶段结束记录

```text
Completed at: 2026-08-21 15:06 CST
Review result: PASS；兼容、安全、迁移、事务、异步取消、资源释放、Redis 并发、日志秘密、浏览器体验、测试覆盖和 P03 范围无剩余阻塞问题
Verification commands: uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（58 passed）；pnpm --filter @en/web type-check；pnpm --filter @en/web build-only；实际浏览器普通/深度/history/角色隔离；git diff --cached --check；敏感/范围扫描
Commit: fc0e503 (P03 主提交)
Branch: codex/p03-ai-service
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P03 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: P03 使用 mock DeepSeek/Bocha 完成确定性自动化与浏览器验收，真实供应商凭证/配额/网络和生产 Nginx 灰度仍须另行授权验证。旧 LangGraph 历史按 D008 不迁移；回退 NestJS 后 FastAPI 窗口的新历史暂不可见。前端构建保留既有 package type/chunk-size 警告，不影响本阶段通过
Next phase start condition: 用户在新执行中明确启动 P04，并重新加载必需 skill
```

## P02 已完成动作

1. 固定 ECDICT 1.0.28 的 tag、完整 commit、下载 URL、文件大小、SHA-256 和 MIT 许可归属。
2. 新增 `WordBook.word`、`Course.value` 唯一键和内部 `frqRank`，保留外部 `frq` 字符串兼容。
3. 实现 UTF-8/BOM CSV 流式读取、字段规范化、考试标签映射、拒绝 JSONL 和每 1,000 条事务 upsert。
4. 以确定性 ID 和自然键 upsert 八门旧课程，保持名称、文案、教师、价格与 `/course/{value}.png`。
5. 创建/检查 `course` bucket、公开只读策略、PNG SHA metadata、稳定对象键与公开 HEAD/MIME 验证。
6. 提供生产禁用的 `en-learning-bootstrap`，串联固定源校验、Alembic、数据、对象、保护表验证与无秘密 JSON 报告。
7. 覆盖坏行、排序边界、批次故障恢复、连续两次幂等、真实 PostgreSQL/MinIO、失败非零与生产保护。
8. 修复同进程 Alembic `fileConfig` 会禁用既有应用 logger 的副作用。
9. 使用完整官方 CSV 在隔离空环境连续执行两次：第一次 770,611 插入，第二次 770,611 skip，0 拒绝。
10. 完成兼容、安全、迁移、事务、异步阻塞、资源释放、幂等、错误/报告、秘密和测试覆盖自审；修正生产拒绝时机、下载字节上限、关闭兜底和对象 metadata/长度复核后完成复测。

## P02 阶段结束记录

```text
Completed at: 2026-08-21 14:26 CST
Review result: PASS；兼容、安全、迁移、事务、异步阻塞、资源释放、幂等、错误/报告、秘密和测试覆盖无剩余阻塞问题
Verification commands: uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（40 passed）；完整 ECDICT 双次 CLI（770,611 insert → 770,611 skip）；git diff --cached --check；敏感/范围扫描
Commit: 8c5bf25 (P02 主提交)
Branch: codex/p02-data-bootstrap
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P02 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: P02 迁移和 bootstrap 只面向空的 development/test 环境；生产 schema 接管仍须 P07 明确授权与基线/stamp 流程。ECDICT 版本升级必须显式更新 D016、大小、SHA-256 和许可证记录
Next phase start condition: 用户在新执行中明确启动 P03，并重新加载必需 skill
```

## P01 已完成动作

1. 建立 Python 3.12 `pyproject.toml`、安全 `.env.example`、本地忽略规则与启动/质量命令。
2. 建立 Core API、AI API 两个 factory 入口，保留 `/api/v1/`、`/ai/v1/` 根契约。
3. 实现 request ID、JSON 日志、统一成功/失败 envelope、验证/HTTP/未知异常映射。
4. 实现不依赖外部服务的 live 与逐项、不泄密的 PostgreSQL/Redis/MinIO ready 检查。
5. 使用 lifespan 管理 SQLAlchemy engine、Redis、MinIO HTTP pool、通用 HTTP 与 LLM HTTP client；应用导入不建立网络连接。
6. 映射 11 个 Prisma 模型，保留物理名称、关系、级联、索引、唯一键、Decimal、DateTime、JSONB 与枚举。
7. 建立仅用于空库的可逆 Alembic 初始迁移，并记录生产基线/stamp 约束。
8. 选定 Taskiq + Redis Stream broker、独立 scheduler，并记录确认、重试、幂等、失败记录与关停边界。
9. 增加配置、契约、健康、生命周期、进程、ORM、worker 重试和真实迁移往返测试；最终 `25 passed`。
10. 完成兼容、安全、迁移、异步、资源、测试和范围自审；修正健康 envelope 默认值、未知异常日志脱敏、SQLAlchemy async extra 和 Uvicorn 信号断言，并完成复测。

## P01 阶段结束记录

```text
Completed at: 2026-08-21 13:52 CST
Review result: PASS；兼容、安全、迁移、异步、资源、测试和范围审查无剩余阻塞问题
Verification commands: uv lock --check --offline；ruff format --check；ruff check；mypy src；pytest -q（25 passed）；git diff --cached --check；敏感/范围扫描
Commit: bb0a24b (P01 主提交)
Branch: codex/p01-fastapi-foundation
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS；P01 主提交已推送，完成记录随当前提交推送
Remaining non-blocking risks: 初始 Alembic 迁移仅适用于空库；生产 schema 接管须在 P07 经批准后比较并 stamp。业务任务退避、死信、幂等和重放仍按计划留在 P05
Next phase start condition: 用户在新执行中明确启动 P02，并重新加载必需 skill
```
