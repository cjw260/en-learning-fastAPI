# FastAPI 重构进度

最后更新：2026-08-21

## 当前执行锁

| 字段 | 值 |
|---|---|
| Active phase | `P01`：FastAPI 工程骨架与数据库基础 |
| Phase status | `IN_PROGRESS` |
| Phase lock | `LOCKED`（本次只允许执行 P01） |
| Allowed scope | `fastapi-backend/` 工程与测试、P01 文档/决策/进度、权威计划状态 |
| Forbidden scope | P02 数据导入、P03+ 业务迁移、NestJS 业务改动、生产部署 |
| Required skill | `en-learning-backend-refactor` |
| Skill status | `LOADED` |
| Skill loaded at | 2026-08-21 13:41 CST（P01 依赖安装后续作重新加载） |
| Next phase | `P02`，即使 P01 完成也不得在本次执行中启动 |

## 阶段状态

| 阶段 | 状态 | 完成提交 | 备注 |
|---|---|---|---|
| P00 仓库、计划与基线 | `COMPLETED` | `984d60e` | 主提交已推送到新 origin 的阶段分支 |
| P01 工程骨架与数据库基础 | `IN_PROGRESS` | — | 当前唯一执行阶段 |
| P02 数据初始化 | `NOT_STARTED` | — | — |
| P03 AI 服务 | `NOT_STARTED` | — | — |
| P04 核心业务 API | `NOT_STARTED` | — | — |
| P05 支付/Socket.IO/worker | `NOT_STARTED` | — | — |
| P06 前端与全链路验收 | `NOT_STARTED` | — | — |
| P07 灰度上线与清理 | `NOT_STARTED` | — | — |

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

无实现或验收阻塞。用户已手动补充 `greenlet 3.5.5`，P01 全部自动化验收和最终自审通过。阶段仍保持 `IN_PROGRESS`，直到当前 P01 文件安全提交并推送到新 `origin`。

## 准确下一动作

仅暂存 P01 代码与 `AGENTS.md`、`docs/fastapi-refactor/DECISIONS.md`、本文件、P01 阶段文件，明确排除 `.agents/`、`.codex/`、`.env`、`.venv` 和缓存；检查暂存 diff 后创建 P01 主提交并推送。推送成功后再记录完成状态并推送完成记录，结束本次执行。

## P01 已完成动作（待验收）

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

## 阶段结束记录模板

```text
Completed at: 2026-08-21
Review result: PASS；仅 13 个 P00 文档进入主提交，无运行时代码、秘密或无关用户文件
Verification commands: 路径检查、空白检查、冲突标记检查、常见密钥检查、git diff --cached --check、远端 commit 对比
Commit: 984d60e (P00 主提交)
Branch: codex/p00-repository-baseline
Remote: origin -> https://github.com/cjw260/en-learning-fastAPI.git
Push result: PASS
Remaining non-blocking risks: 旧 NestJS 依赖未安装，无法执行运行时 API 基线；仓库原本没有测试/CI
Next phase start condition: 用户在新执行中明确启动 P01，并重新加载必需 skill
```
