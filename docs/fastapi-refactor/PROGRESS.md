# FastAPI 重构进度

最后更新：2026-08-21

## 当前执行锁

| 字段 | 值 |
|---|---|
| Active phase | `P03`：AI 服务迁移 |
| Phase status | `IN_PROGRESS` |
| Phase lock | `P03 ONLY` |
| Allowed scope | `/ai/v1` prompt/chat/history、JWT 身份、LLM/搜索适配、SSE、AI 历史迁移、必要前端 token 适配、测试与 AI 灰度文档 |
| Forbidden scope | P04 核心业务、P05 支付/Socket.IO/worker、P06 全链路适配、生产部署和切流 |
| Required skill | `en-learning-backend-refactor` |
| Skill status | `LOADED` |
| Skill loaded at | 2026-08-21（P03 新执行重新加载） |
| Next phase | `P04`，仅在 P03 完成并由用户在新的执行中明确启动 |

## 阶段状态

| 阶段 | 状态 | 完成提交 | 备注 |
|---|---|---|---|
| P00 仓库、计划与基线 | `COMPLETED` | `984d60e` | 主提交已推送到新 origin 的阶段分支 |
| P01 工程骨架与数据库基础 | `COMPLETED` | `bb0a24b` | 主提交已推送到 `origin/codex/p01-fastapi-foundation` |
| P02 数据初始化 | `COMPLETED` | `8c5bf25` | 主提交已推送到 `origin/codex/p02-data-bootstrap` |
| P03 AI 服务 | `IN_PROGRESS` | — | 用户已明确启动；阶段锁已建立 |
| P04 核心业务 API | `NOT_STARTED` | — | — |
| P05 支付/Socket.IO/worker | `NOT_STARTED` | — | — |
| P06 前端与全链路验收 | `NOT_STARTED` | — | — |
| P07 灰度上线与清理 | `NOT_STARTED` | — | — |

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

无 P03 阻塞。实现、实际浏览器验收、最终自动化与前端构建均通过；正在完成最终暂存范围/敏感信息审查和安全推送。

## 准确下一动作

只暂存 P03 文件，完成最终 staged diff/秘密扫描后创建主提交并推送；随后记录完成提交并结束，不启动 P04。

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
