# en-learning FastAPI 后端重构权威计划

> 本文件是本仓库 NestJS → FastAPI 后端重构的唯一阶段依据。任何新对话、阶段启动、阶段续作、返工、验收、审查、提交或推送，都必须先完整读取本文件。

## 1. 当前状态

| 项目 | 当前值 |
|---|---|
| 计划版本 | 1.0 |
| 最后更新 | 2026-08-21 |
| 当前阶段 | P02：开发数据初始化 |
| 阶段状态 | `IN_PROGRESS` |
| 本次唯一允许执行的阶段 | `P02` |
| 必需 skill | `en-learning-backend-refactor` |
| 本次 skill 状态 | `LOADED`（2026-08-21，当前任务） |
| 下一阶段 | P03：AI 服务迁移（尚未授权启动） |

阶段状态只允许使用：`NOT_STARTED`、`IN_PROGRESS`、`BLOCKED`、`COMPLETED`。

## 2. 不可绕过的执行规则

### 2.1 Skill 门禁

开始或继续任何阶段前，必须在当前对话中重新加载并遵守 `en-learning-backend-refactor` skill；上一对话、上一任务或上一阶段的加载状态不继承。

如果 skill 不存在、不可读取或尚未加载：

- 将当前阶段标记为 `BLOCKED`。
- 禁止编码、数据库迁移、数据导入、阶段验收、提交和推送。
- 向用户说明阻塞原因，不得用聊天中的临时指令绕过门禁。

加载 skill 后，必须依次完成：

1. 确认 Git 仓库根目录。
2. 验证 `server/nest-cli.json`、`server/package.json`、`apps/web`、`packages/common` 四个仓库标识。
3. 完整读取本文件及当前阶段文档、进度文档。
4. 检查分支、`git status`、相关 diff 和最近提交，保护用户已有改动。
5. 锁定本次唯一阶段，明确范围、非范围、风险和验证方法。
6. 涉及 NestJS 与 FastAPI 技术映射时，读取 `.agents/skills/en-learning-backend-refactor/references/framework-parity.md`。
7. 完成以上步骤后才允许修改阶段范围内的文件。

### 2.2 单阶段执行锁

- 每一次执行只能对一个阶段进行编码或迁移，禁止同时执行两个阶段。
- 阶段必须按 P00 → P01 → P02 → P03 → P04 → P05 → P06 → P07 顺序执行。
- 即使当前阶段提前完成，也只能更新进度、完成验收、审查、提交并结束；不得在同一次执行中开始下一阶段。
- 只有当前阶段的全部验收标准通过、审查完成、复测通过并安全推送后，才可标记 `COMPLETED`。
- 下一阶段必须由用户在新的执行中明确提出，并重新通过 skill 门禁。
- 失败、跳过或无法验证的验收项都会阻止进入下一阶段；不得为了宣布完成而删除或弱化验收标准。

### 2.3 兼容、安全与数据原则

- 迁移期间保留现有 NestJS 后端作为可回退基线，不原地覆盖 `server/`。
- FastAPI 新实现放入独立目录，采用两个 HTTP 应用和独立后台任务子系统。
- 对前端保持既有 URL、HTTP 方法、主要请求字段、响应包裹、状态码和实时事件兼容；安全漏洞修复可以改变不安全行为，但必须记录影响和前端适配。
- 任何密钥、`.env`、生产数据库内容、用户隐私数据、支付凭证和第三方凭证都不得提交。
- 当前电脑没有生产数据库数据；开发数据库从迁移、ECDICT 词库、现有课程 seed 和课程图片确定性重建。
- 用户、学习记录、支付记录、埋点和历史聊天等业务数据不伪造；AI 历史允许在本次重构中清空。
- WordBook 的 `frq` 按数值升序排序，缺失值、非数值和 `0` 排在有效正数之后；API 外部字段兼容现有前端契约。
- 生产部署、数据库切换、Nginx 切流和旧服务下线必须另获用户明确授权；完成代码阶段不等于获准部署。

## 3. 已锁定的架构与迁移决策

| 事项 | 决策 |
|---|---|
| 迁移方式 | 分阶段灰度迁移，AI 服务优先 |
| HTTP 服务 | Core API 保持 `/api/v1`；AI API 保持 `/ai/v1` |
| 后台任务 | Redis 支撑的独立 worker/调度子系统，不在 Web 进程内执行持久任务 |
| 生产运行 | systemd + Uvicorn；旧 NestJS/PM2 在灰度期保留作为回退 |
| 数据库 | PostgreSQL；SQLAlchemy 2.x async + asyncpg + Alembic |
| 缓存/队列 | Redis；具体 Python 任务库在 P01 通过最小验证后锁定 |
| 对象存储 | 兼容当前 MinIO bucket 和对象 URL 规则 |
| 实时通信 | 保持 Socket.IO 客户端协议和 `paymentSuccess` 事件兼容，使用 Redis 跨进程广播 |
| AI 流式输出 | 保持 SSE 事件载荷兼容，正确处理断开、超时和上游失败 |
| 认证 | 保持 Bearer access/refresh token 流程；密码改为安全哈希；服务端不再信任客户端传入的用户身份 |
| 词库 | 使用 GitHub `skywind3000/ECDICT` 作为 WordBook 数据源；导入时固定来源版本并记录校验值 |
| 课程 | 使用现有 `server/prisma/seed.ts` 与 `server/prisma/assets/*.png` 幂等重建 |
| 新远端 | `https://github.com/cjw260/en-learning-fastAPI.git`，继承当前 Git 历史 |
| 旧远端 | 保留并改名为 `nest-origin`，禁止破坏或强推旧仓库 |

详细决策与变更记录见 `docs/fastapi-refactor/DECISIONS.md`。

## 4. 目标架构

```text
Vue Web / Tracker SDK
        │
        ▼
      Nginx
        ├── /api/v1 ──► FastAPI Core API（迁移期可回退 NestJS :3000）
        ├── /ai/v1  ──► FastAPI AI API（迁移期可回退 NestJS :3001）
        └── Socket.IO ► FastAPI Socket.IO ASGI 层
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         PostgreSQL      Redis       MinIO
              ▲           │
              └──── Background Worker/Scheduler
```

计划中的 FastAPI 目录边界：

```text
fastapi-backend/
├── pyproject.toml
├── alembic.ini
├── src/en_learning/
│   ├── api/       # Core API 入口和业务模块
│   ├── ai/        # AI API、SSE、提示词和历史
│   ├── worker/    # 邮件摘要、重试任务与调度
│   ├── db/        # SQLAlchemy 模型、会话、迁移支持
│   ├── schemas/   # Pydantic 请求/响应契约
│   ├── services/  # MinIO、Redis、邮件、支付、LLM 等适配器
│   └── common/    # 配置、认证、错误、响应、日志、生命周期
├── migrations/
├── scripts/
└── tests/
```

实际创建目录属于 P01，本阶段不得提前创建运行时代码。

## 5. 阶段总览

| 阶段 | 状态 | 目标 | 本阶段主要产物 |
|---|---|---|---|
| P00 仓库、计划与基线 | `COMPLETED` | 建立新仓库、权威计划、旧系统契约和可回退基线 | 本文件、进度/决策/阶段文档、旧系统基线、新远端 |
| P01 工程骨架与数据库基础 | `COMPLETED` | 建立可测试、可配置、可迁移的 FastAPI 基础 | Python 工程、双应用、worker 骨架、SQLAlchemy/Alembic、健康检查 |
| P02 数据初始化 | `IN_PROGRESS` | 在无本地业务数据时确定性重建开发数据 | ECDICT 导入、课程 seed、MinIO 图片、初始化报告 |
| P03 AI 服务迁移 | `NOT_STARTED` | 优先迁移 AI API、SSE 和新聊天历史 | `/ai/v1`、LLM 适配、SSE、历史、AI 灰度验证 |
| P04 核心业务 API | `NOT_STARTED` | 迁移用户、词库、课程、学习与埋点 | `/api/v1` 核心路由、鉴权、上传、业务事务 |
| P05 支付、实时通信与任务 | `NOT_STARTED` | 迁移高风险异步和外部集成 | 支付回调、Socket.IO、Redis 广播、worker/调度 |
| P06 前端适配与全链路验收 | `NOT_STARTED` | 完成必要前端安全适配和跨服务回归 | 前端适配、契约/E2E/并发测试、验收报告 |
| P07 灰度上线与旧后端清理 | `NOT_STARTED` | 可观测、可回滚地切换生产流量 | systemd/Nginx、备份恢复、灰度记录、回退演练、清理决定 |

## 6. 各阶段实施步骤与验收标准

### P00：仓库、计划与旧系统基线

状态：`COMPLETED`

目标：在不编写 FastAPI 运行时代码的前提下，建立所有后续任务可复用的唯一计划、进度记录、旧系统契约和新仓库边界。

范围：

- 更新本文件为权威计划并保留部署备忘。
- 建立 `docs/fastapi-refactor/` 下的总览、进度、决策、旧系统基线和逐阶段文档。
- 盘点现有路由、响应格式、鉴权、数据库模型、Seed、SSE、Socket.IO、队列、外部服务、前端调用和部署方式。
- 将旧 `origin` 保留为 `nest-origin`，把新 FastAPI 仓库配置为 `origin`，继承当前历史。
- 建立阶段分支，完成 P00 文档验收、审查、提交和推送。

非范围：

- 不创建 FastAPI 项目、不安装 Python 依赖、不修改业务实现。
- 不连接、导出或修改生产数据库。
- 不部署服务器、不修改 Nginx/PM2/systemd、不切换生产流量。

实现步骤：

1. 验证仓库标识、当前分支、工作区、远端和最近提交。
2. 从 NestJS controller、service、共享类型、Prisma schema、前端 API 和部署脚本提取基线。
3. 将阶段顺序、单阶段锁、skill 门禁、架构决策、验收与回退写入持久文档。
4. 记录现有构建/测试能力和本地依赖缺口，不把环境缺失伪装为成功。
5. 安全配置新旧远端，验证新仓库继承历史且旧仓库未被改写。
6. 校验文档链接、敏感信息、阶段一致性和最终 diff。

验收标准：

- [x] 当前任务已加载 `en-learning-backend-refactor`，仓库四个标识全部存在。
- [x] 本文件明确给出当前阶段、范围、非范围、顺序、强制 skill 和验收门禁。
- [x] 每个阶段均有目标、实现步骤、验收标准、测试方式和回退方案。
- [x] 旧系统基线覆盖 HTTP、SSE、Socket.IO、数据库、Seed、外部依赖、前端调用与部署。
- [x] `PROGRESS.md` 能让新对话明确知道当前阶段、最后动作、证据、阻塞和下一动作。
- [x] 旧仓库以 `nest-origin` 保留；新仓库为 `origin`；新仓库包含原 Git 历史；未执行 force push。
- [x] 未提交 `.env`、密钥、生产数据、`.codex/` 或无关用户改动。
- [x] P00 文档检查通过，最终 diff 已审查；主提交 `984d60e` 已推送。
- [x] 本次没有开始 P01 或修改 FastAPI 运行时代码。

测试方式：文档路径/链接检查、`git diff --check`、敏感文件检查、Git 远端与历史检查、最终 `git status` 与提交检查。

回退：文档提交通过普通 revert 回退；本地远端可改回旧 URL；旧 `nest-origin` 和旧 GitHub 仓库不得删除或强推。

### P01：FastAPI 工程骨架与数据库基础

状态：`COMPLETED`

目标：建立两个 ASGI 应用、独立 worker 边界、共享基础设施以及可重复执行的数据库迁移能力。

实现步骤：

1. 创建 `fastapi-backend/`、锁定 Python 3.12 和依赖版本，配置格式化、静态检查和 pytest。
2. 建立 Core API、AI API、worker 三个独立入口，共用 typed settings、日志、request ID、错误处理和响应包裹。
3. 使用 lifespan 管理数据库、Redis、MinIO、HTTP/LLM 客户端的初始化和释放；禁止 import 时建立外部连接。
4. 实现 `/health/live` 和 `/health/ready`；存活检查不依赖外部服务，就绪检查分别报告依赖状态且不泄露凭证。
5. 将 Prisma 数据模型映射为 SQLAlchemy 2.x async 模型，建立 Alembic 初始迁移、约束、索引、枚举和事务会话。
6. 为 `/api/v1` 与 `/ai/v1` 建立兼容的路由骨架、Pydantic schema、响应 envelope 和异常映射，但不提前实现业务。
7. 通过小型验证锁定 Redis worker 库，并记录定时任务、重试、幂等和优雅停机策略。
8. 增加开发环境模板与启动命令；仅提供变量名和安全默认值，不提交秘密。

验收标准：

- [x] 重新加载 skill，且本次只执行 P01。
- [x] Core API、AI API 和 worker 可分别启动、优雅停止，模块导入无外部副作用。
- [x] `/health/live` 正常；依赖可用/不可用时 `/health/ready` 给出正确状态。
- [x] Alembic 能对空 PostgreSQL 升级到最新版本并完整降级后再次升级。
- [x] ORM 表、关系、唯一约束、索引、Decimal/DateTime/JSON/枚举语义与批准后的 schema 一致。
- [x] 统一成功/失败响应、状态码、路径、时间戳和验证错误有自动化测试。
- [x] 配置缺失会快速失败且不打印密钥；测试、lint、类型检查通过。
- [x] 没有实现 P02 数据导入或 P03+ 业务功能。

测试方式：pytest 单元/集成测试、Alembic upgrade/downgrade、应用启动与信号停止、配置失败测试、lint 和类型检查。

回退：删除独立 FastAPI 目录或 revert P01 提交即可；NestJS `server/` 与生产服务不受影响。

### P02：开发数据初始化

状态：`IN_PROGRESS`

目标：无需生产数据库备份，也能通过受控、幂等、可审计的流程重建词库和课程基础数据。

实现步骤：

1. 固定 ECDICT 来源仓库、commit/tag、文件校验值和许可证说明；禁止运行时临时拉取不固定的最新版。
2. 实现流式/分批词库导入，规范空值、布尔标签、文本编码和 `frq` 数值；对无效行记录原因而不是静默丢弃。
3. 为单词建立稳定 upsert 键和批次事务，重复执行不产生重复数据；失败可从明确批次恢复。
4. 按数值升序定义 `frq` 排序，缺失、非数值及 `0` 统一排到有效正数之后，并用边界样例锁定行为。
5. 将现有八门课程 seed 改造成幂等 upsert，保持 `value`、文案、教师、价格和对象 URL 兼容。
6. 创建/检查 MinIO `course` bucket 和只读策略，按内容类型上传八张现有 PNG；重复运行不会产生脏对象。
7. 输出初始化报告：来源版本、校验值、导入/更新/跳过/失败数、课程数、对象数和总耗时。

验收标准：

- [x] 重新加载 skill，且本次只执行 P02。
- [x] 全新数据库可一条受控命令完成迁移、ECDICT 导入和课程/图片初始化。
- [x] ECDICT 来源版本与校验值被记录；编码、字段映射、拒绝行可审计。
- [x] 连续执行两次后 WordBook、Course 和 MinIO 对象数量不重复，关键数据一致。
- [x] 八门课程及 `gk/zk/gre/toefl/ielts/cet6/cet4/ky` 图片均可访问且 MIME 正确。
- [x] `frq` 正数数值升序，null/空/非数值/0 在后；分页排序稳定。
- [x] 不生成虚假用户、学习、支付、埋点或聊天历史。
- [x] 初始化失败返回非零状态并保留可重跑状态；自动化测试通过。

测试方式：临时 PostgreSQL/MinIO 集成测试、导入两次幂等测试、字段映射/坏行/排序单测、对象 HEAD 检查、初始化报告校验。

回退：仅清理有明确导入批次/开发环境标识的数据和对象；禁止对未确认环境执行全库删除。

### P03：AI 服务迁移

状态：`NOT_STARTED`

目标：首先以 FastAPI 替换 AI HTTP 服务，同时保持 `/ai/v1`、SSE 载荷和前端体验兼容。

实现步骤：

1. 迁移健康首页和 `/ai/v1/prompt/list`，固定角色列表、顺序和统一响应 envelope。
2. 迁移 `/ai/v1/chat` 请求 schema；验证 `deepThink`、`webSearch`、`role`、`content`，鉴权后由服务端确定 userId。
3. 建立 LLM 适配层，隔离 DeepSeek/LangChain 具体实现，设置连接、首 token、总时长和重试边界。
4. 用 `StreamingResponse` 输出 SSE，保持 `{content, role: "ai", type: "reasoning"|"chat"}` 载荷；处理心跳、反向代理缓冲、断连取消和上游异常。
5. 建立新的聊天历史/checkpoint schema；按已确认决策不迁移旧历史，但新历史必须按用户和角色隔离。
6. 迁移 `/ai/v1/chat/history`，保留返回形状；禁止读取其他用户历史，限制输入长度和历史窗口。
7. 记录 token/延迟/错误等非敏感日志，不记录完整提示词、令牌、密钥或不必要的个人内容。
8. 在本地契约测试通过后准备只针对 `/ai/` 的灰度配置和旧 AI 回退路径，但未经授权不修改生产。

验收标准：

- [ ] 重新加载 skill，且本次只执行 P03。
- [ ] prompt、chat SSE、history 的路径、方法、主要字段和响应形状与前端兼容。
- [ ] reasoning/chat 分片、顺序、结束、断连取消、超时和上游错误均有自动化测试。
- [ ] AI 接口需要有效身份，客户端 userId 不能越权读取或写入他人历史。
- [ ] 旧历史为空是已记录的预期行为；新历史在重启后可恢复并按角色隔离。
- [ ] DeepSeek 不可用、Redis/PostgreSQL 不可用时错误可控，不泄露密钥或内部堆栈。
- [ ] 前端聊天模式、普通/深度思考流和历史显示通过实际浏览器验证。
- [ ] 未迁移 P04 核心业务或 P05 支付/Socket.IO/任务。

测试方式：mock LLM 单测、SSE 流式集成测试、数据库历史测试、鉴权/越权测试、断连/超时测试、前端浏览器验收。

回退：Nginx `/ai/` 指回 NestJS :3001；新历史表可保留，不影响旧服务；不得破坏 Core API。

### P04：核心业务 API 迁移

状态：`NOT_STARTED`

目标：迁移除支付、实时通信和后台任务外的 Core API，并在保持前端兼容的同时修复认证、密码和上传安全问题。

实现步骤：

1. 实现统一 JWT access/refresh 验证、token 类型检查、过期语义和当前用户依赖；密码使用安全哈希，不再明文存储或返回。
2. 迁移登录、注册、刷新 token、更新用户；处理手机号/邮箱唯一冲突和 refresh token 滥用。
3. 迁移头像上传并强制鉴权，限制大小、MIME、扩展名和对象键；清理失败上传，返回现有 `previewUrl/databaseUrl` 形状。
4. 迁移课程列表和“我的课程”，保持 Decimal 序列化、课程图片 URL 和购买状态语义。
5. 迁移 WordBook 查询、过滤、分页和稳定排序；落实 `frq` 数值排序及尾部无效值规则。
6. 迁移学习课程取词和掌握单词接口；以当前 JWT 用户为准，使用事务和唯一约束保证重复提交幂等，正确更新 wordNumber。
7. 迁移 UV、PV、event、performance、error 埋点；增加 schema 边界、批量/速率限制、载荷大小限制和隐私过滤。
8. 为所有路由建立 NestJS-FastAPI 契约夹具，覆盖成功、验证失败、401、403、404、409 和依赖失败。

验收标准：

- [ ] 重新加载 skill，且本次只执行 P04。
- [ ] 用户、课程、词库、学习、埋点所有既有路由均有契约清单和自动化测试。
- [ ] 成功 envelope、错误 envelope、状态码、日期/Decimal/null 序列化满足批准后的兼容基线。
- [ ] 新密码仅存安全哈希；登录、刷新、token 类型、过期、伪造 token 和越权均正确处理。
- [ ] 头像上传必须鉴权，危险文件、超限文件和对象覆盖被拒绝或隔离。
- [ ] WordBook 过滤、分页、稳定 `frq` 排序与 ECDICT 标签结果正确。
- [ ] 学习接口校验课程购买权，重复掌握不重复计数，并发下不破坏唯一约束。
- [ ] 埋点接口对错误/超大载荷可控且不在日志泄露敏感数据。
- [ ] 未实现 P05 支付、Socket.IO 或后台任务。

测试方式：API 契约/集成测试、JWT 和权限测试、上传安全测试、事务并发测试、分页排序测试、前端核心流程冒烟测试。

回退：Nginx `/api/` 指回 NestJS :3000；新密码策略和任何 schema 差异必须在切流前提供兼容/回退说明。

### P05：支付、Socket.IO 与后台任务

状态：`NOT_STARTED`

目标：迁移最需要幂等、跨进程协调和外部失败处理的支付、实时通知、邮件摘要与定时任务。

实现步骤：

1. 迁移支付创建，服务端从数据库读取课程、金额和主题可信数据；客户端金额仅作兼容输入，不作为结算依据。
2. 迁移支付宝异步通知，按原始字段验签，校验商户、应用、订单号、金额和状态；事务性更新 PaymentRecord/CourseRecord。
3. 使用唯一键和状态机实现回调幂等、重复/乱序通知处理，并在事务提交后才发布支付成功事件。
4. 使用 `python-socketio` 保持连接方式、房间和 `paymentSuccess` 事件兼容；用 JWT 绑定用户身份，不信任裸 userId。
5. 使用 Redis manager 在多个 Uvicorn 实例和 worker 间广播，验证断线重连和同一用户多标签页行为。
6. 迁移邮件摘要与定时任务到独立 Redis worker/调度进程，设计唯一任务键、重试退避、超时、死信/失败记录和分布式锁。
7. 处理邮件、Redis、支付宝和 Socket.IO 任一依赖失败，保证支付事实不因通知失败回滚或丢失，并支持补偿重放。
8. 添加结构化审计日志，脱敏订单、用户、签名和邮件内容。

验收标准：

- [ ] 重新加载 skill，且本次只执行 P05。
- [ ] 支付金额由服务端课程数据确定；伪造金额、订单和用户被拒绝。
- [ ] 支付宝有效/无效签名、重复、乱序、金额不符和未知订单场景全部通过测试。
- [ ] 订单与课程购买更新在单事务内，重复回调不会重复购买或重复通知。
- [ ] 现有前端 Socket.IO 客户端能连接、重连、加入正确用户房间并收到 `paymentSuccess`。
- [ ] 多 Uvicorn 实例通过 Redis 正确跨进程广播；未认证用户不能订阅他人事件。
- [ ] worker 重启后任务不静默丢失；重试、幂等、调度锁和失败记录可验证。
- [ ] 支付成功但即时通知失败时可通过重连查询/补偿恢复最终一致性。

测试方式：支付宝签名夹具、数据库事务/幂等并发测试、Socket.IO 多进程集成测试、Redis/邮件故障注入、worker 重启与重复投递测试。

回退：支付流量整体切回 NestJS，避免双写；保留新服务消费暂停开关和事件重放记录；不得删除支付审计数据。

### P06：前端适配与全链路验收

状态：`NOT_STARTED`

目标：完成安全修复所需的最小前端改动，并证明 FastAPI 后端可以支撑现有完整用户流程。

实现步骤：

1. 保持 `/api/v1`、`/ai/v1` 和 Socket.IO 基础地址不变，集中调整 Axios/fetch-event-source/socket.io 的 token 携带与错误处理。
2. 修复 token 刷新并发队列：成功后重放原请求，失败时拒绝并清空所有等待请求，避免 Promise 悬挂。
3. AI SSE 携带认证并正确处理 reasoning/chat、结束、取消、401、超时和重试，不重复渲染消息。
4. Socket.IO 握手改为受保护认证参数，支付成功后同时通过 API 查询确认最终状态。
5. 覆盖注册登录、资料头像、课程列表/购买、支付通知、课程学习/掌握、词库搜索分页、AI 聊天历史和埋点全链路。
6. 比较 NestJS 与 FastAPI 的关键契约夹具；任何批准的安全差异写入迁移说明。
7. 进行并发、性能和资源泄漏检查，确定 Uvicorn worker 数、数据库池、Redis 和超时参数建议。
8. 生成完整验收报告、已知非阻塞风险和 P07 上线前检查表。

验收标准：

- [ ] 重新加载 skill，且本次只执行 P06。
- [ ] 前端生产构建、类型检查和新增自动化测试通过。
- [ ] 关键用户流程在浏览器中全部通过，加载/空/错误/过期/重连状态可用。
- [ ] NestJS 与 FastAPI 契约差异为零或全部属于明确批准并记录的安全修复。
- [ ] refresh 并发、SSE 取消、Socket.IO 重连和支付最终确认没有悬挂或重复副作用。
- [ ] 关键 API 的并发和延迟达到验收报告中锁定的基线，连接池和资源无持续泄漏。
- [ ] P07 所需 systemd、Nginx、监控、备份与回退清单已准备，但未改生产环境。

测试方式：前端 build/type-check、API 契约套件、Playwright 或等价浏览器 E2E、并发/负载冒烟、长连接与资源监控。

回退：前端适配必须与旧后端兼容；若不能兼容，保留可独立回退的前端构建产物和配置说明。

### P07：灰度上线与旧后端清理

状态：`NOT_STARTED`

目标：在用户明确授权后，以可观测、可回滚方式部署 FastAPI，完成灰度观察与旧服务处置。

实现步骤：

1. 上线前备份 PostgreSQL、验证恢复流程，保存当前 Nginx、PM2、环境和部署脚本配置；确认 MinIO/Redis 健康。
2. 为 Core API、AI API、worker 和调度器创建最小权限 systemd unit，配置工作目录、环境文件、重启、超时和日志。
3. 在旁路端口启动 FastAPI，执行健康、迁移、种子校验和内部冒烟；不抢占旧 NestJS 端口。
4. 先灰度 `/ai/`，再灰度 `/api/`；每次只切一个路由组，监控错误率、P95、SSE、Socket.IO、支付和资源。
5. 设置明确观察窗口与回退阈值；触发阈值时恢复 Nginx upstream 并保留证据，不在故障中临时改数据。
6. 在支付真实小额验证、任务调度、重启恢复和回退演练通过后再完成全量切换。
7. 达到稳定观察期并经用户确认后，才停止旧 PM2 服务；先归档配置和日志，再决定是否删除旧代码。
8. 更新部署文档、运维命令、服务端口、备份/恢复和故障处置说明。

验收标准：

- [ ] 重新加载 skill，且本次只执行 P07；已取得明确生产部署授权。
- [ ] 数据库备份可恢复，Nginx/PM2 配置有可用备份，回退命令经过演练。
- [ ] systemd 服务以非 root 身份运行，启动、停止、重启、开机启动和日志轮转正常。
- [ ] AI 与 Core 分步灰度，每一步都有时间、指标、结果和操作者记录。
- [ ] 健康、错误率、P95、数据库连接、Redis、SSE、Socket.IO、支付和 worker 指标在阈值内。
- [ ] 真实支付与异步通知闭环通过，重复回调不产生重复权益。
- [ ] 回退演练能在目标时间内恢复旧 NestJS 服务，且不丢失已确认的支付/学习数据。
- [ ] 稳定观察期结束并获得用户确认前，旧 PM2 服务和旧仓库均未删除。
- [ ] 部署与运维文档已更新，最终审查、复测、提交和推送完成。

测试方式：备份恢复演练、systemd 生命周期、Nginx upstream 切换、生产旁路冒烟、指标观察、真实小额支付、故障回退演练。

回退：恢复已保存的 Nginx upstream 和 PM2 NestJS 服务；暂停 FastAPI worker 防止双消费；按审计记录处理切换窗口内的数据，不做盲目数据库回滚。

## 7. 进度记录规范

详细进度存放在 `docs/fastapi-refactor/PROGRESS.md`。每次阶段任务必须更新：

- 当前阶段及状态。
- 本次是否重新加载必需 skill、加载时间。
- 阶段锁和允许范围。
- 本次开始前的 Git 状态及需要保护的用户改动。
- 验收标准逐条状态、验证命令和证据。
- 已完成内容、最后一个成功动作、阻塞点和准确的下一动作。
- 审查结论、提交哈希、分支、远端和推送结果。

新对话首先读取本文件，再读取 `docs/fastapi-refactor/PROGRESS.md` 和当前阶段文件；不得根据聊天记忆猜测进度。

## 8. 阶段完成与 Git 规则

阶段完成顺序固定为：

1. 完成当前阶段范围。
2. 逐条执行验收并保存证据。
3. 阅读最终 diff，进行安全、兼容、事务、异步、资源和测试自审。
4. 修复问题并重跑受影响验收。
5. 只暂存当前阶段文件，排除 `.env`、密钥、生产数据、工具状态和无关用户改动。
6. 若仍在 `main`，创建 `codex/<阶段>-<名称>` 分支。
7. 创建包含阶段编号和结果的提交并推送到新 `origin`。
8. 更新阶段为 `COMPLETED` 后结束本次执行，等待用户另行启动下一阶段。

未经用户明确要求，不自动合并主分支、不部署生产环境、不删除旧仓库、不停止旧服务。

## 9. 当前 P00 已知基线摘要

- 旧后端：NestJS 11 monorepo，`server` 与 `ai` 两个应用。
- 现有端口：Core API 3000，AI API 3001。
- 全局前缀：`/api/v1` 与 `/ai/v1`。
- 统一成功响应：`timestamp/path/message/code/success/data`；失败响应不含 `data`。
- 数据：PostgreSQL + Prisma；当前本地没有业务数据库数据。
- 基础设施：Redis、MinIO、支付宝、邮件、DeepSeek/LangChain、BullMQ、Socket.IO、SSE。
- 现有数据初始化：八门课程及八张图片；WordBook 尚无可复现完整初始化流程。
- 前端：Vue 3/Vite，通过同源 `/api/v1`、`/ai/v1` 和环境变量 Socket URL 调用后端。
- 测试/CI：仓库当前没有测试文件，也没有 GitHub Actions 配置。
- 本地构建基线：Node `v24.18.0`、pnpm `10.32.1`；尚未安装工作区依赖，Nest 构建报 `Command "nest" not found`。
- 当前需保护的未跟踪内容：`.agents/`、`.codex/`；除非用户另行授权，不纳入阶段提交。

完整路由和行为记录将在 P00 的 `docs/fastapi-refactor/LEGACY_BASELINE.md` 中维护。

## 10. 生产部署备忘（旧 NestJS 基线，P07 前不得擅自改动）

### 服务器信息

| 项目 | 信息 |
|---|---|
| IP | 101.96.211.198 |
| 系统 | Ubuntu 24.04 |
| 面板 | 宝塔面板，端口 **28100** |
| 项目路径 | `/www/wwwroot/101.96.211.198/` |

### 当前服务运行方式

| 服务 | 管理方式 | 端口 | 说明 |
|---|---|---|---|
| MinIO | Docker | 9000, 9001 | `/www/docker/docker-compose.yml` |
| Redis | Docker | 6379 | `/www/docker/docker-compose.yml` |
| en-server | PM2 | 3000 | cluster 模式，4 实例 |
| en-ai | PM2 | 3001 | cluster 模式，4 实例 |
| PostgreSQL | 宝塔 | 5432 | 未容器化 |
| Nginx | 宝塔 | 80 | 未容器化 |

### Docker 管理

```bash
cd /www/docker
docker compose up -d
docker compose restart
docker compose logs
docker compose down  # 不要轻易执行
```

### NestJS 构建产物路径

| 服务 | 启动路径 | PM2 名称 |
|---|---|---|
| en-server | `dist/apps/server/apps/server/src/main.js` | en-server |
| en-ai | `dist/apps/ai/apps/ai/src/main.js` | en-ai |

```text
server/dist/
└── apps/
    ├── ai/apps/ai/src/main.js
    └── server/apps/server/src/main.js
```

### 当前启动/重启命令

```bash
cd /www/wwwroot/101.96.211.198/server
pm2 delete all && pm2 save --force
pm2 start dist/apps/server/apps/server/src/main.js --name en-server -i max
pm2 start dist/apps/ai/apps/ai/src/main.js --name en-ai -i max
pm2 save && pm2 startup
```

### 当前一键部署

```bash
bash /www/wwwroot/101.96.211.198/deploy.sh
```

### 常用运维命令

```bash
pm2 status
pm2 logs en-server --lines 20
ss -tlnp | grep -E "3000|3001|6379|9000|80|5432"
systemctl status nginx
docker ps
```

### 敏感信息

`.env` 位于 `server/.env`，禁止提交。其中包含数据库密码、JWT 密钥、MinIO 凭证、DeepSeek API Key、支付宝密钥和邮箱密码。
