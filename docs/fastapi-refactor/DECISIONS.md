# FastAPI 重构决策记录

最后更新：2026-08-21

本文件记录已确认决策。若要改变决策，必须先由用户明确提出，再更新根 `AGENTS.md`、本文件和受影响阶段的验收标准。

## D001：采用分阶段灰度迁移

- 状态：已确认
- 决策：保留 NestJS 作为回退基线，在独立目录实现 FastAPI；先 AI，后 Core API，最后支付与异步系统。
- 原因：降低一次性重写的接口、数据、支付和实时通信风险。
- 影响：迁移期存在两套后端，必须保持路径和契约兼容，并避免双写/双消费。

## D002：每次执行只允许一个阶段

- 状态：已确认，硬门禁
- 决策：任何一次任务只允许修改一个阶段；完成后不得顺手进入下一阶段。
- 影响：每个阶段独立加载 skill、验收、审查、提交和推送；下一阶段需要用户在新执行中启动。

## D003：强制使用重构 skill

- 状态：已确认，硬门禁
- 决策：开始或继续任一阶段，必须在当前对话重新加载 `en-learning-backend-refactor`。
- 影响：未加载或不可读取时阶段为 `BLOCKED`，禁止编码和提交；旧会话的加载状态不继承。

## D004：两个 HTTP 应用与独立 worker 子系统

- 状态：已确认
- 决策：保持 Core API 与 AI API 独立部署；持久后台任务进入 Redis 支撑的独立 worker/调度子系统。
- 影响：共享配置、数据库和响应契约，但进程生命周期与扩缩容分离；不能用 FastAPI `BackgroundTasks` 代替可靠队列。

## D005：保持外部契约，允许安全修复

- 状态：已确认
- 决策：保留 `/api/v1`、`/ai/v1`、主要 schema、响应 envelope、SSE 和 Socket.IO 事件。明文密码、未认证上传、客户端 userId 信任、支付金额信任等问题必须修复。
- 影响：前端可能需要补充 AI/SSE/Socket.IO token，但不应重写业务页面或改变公共 URL。

## D006：开发数据确定性重建

- 状态：已确认
- 决策：本地不依赖生产数据库副本。WordBook 使用 GitHub `skywind3000/ECDICT`；课程使用现有 Prisma seed 与八张 PNG。
- 影响：导入器必须固定来源版本、记录校验值、可审计、幂等、可重跑。用户、学习、支付、埋点和聊天历史不伪造。

## D007：WordBook 频率排序

- 状态：已确认
- 决策：`frq` 按数值升序；正数有效值优先，null、空值、非数值和 `0` 在尾部；分页必须稳定。
- 影响：数据库内部可增加规范化数值列/表达式，但对 API 继续提供兼容字段。

## D008：AI 历史不迁移

- 状态：已确认
- 决策：旧 LangGraph checkpoint/history 可以清空；FastAPI 上线后建立新的持久历史。
- 影响：P03 不承担旧历史转换，但必须验证新历史隔离、持久化与恢复。

## D009：生产使用 systemd + Uvicorn

- 状态：已确认
- 决策：FastAPI 使用 systemd 管理 Uvicorn 和 worker；Redis、MinIO 继续 Docker；PostgreSQL/Nginx 继续宝塔管理。
- 影响：P07 需要独立 unit、环境文件、日志、优雅停机和回滚；灰度期保留 PM2 NestJS。

## D010：新 GitHub 仓库继承历史

- 状态：已确认
- 决策：新 `origin` 为 `https://github.com/cjw260/en-learning-fastAPI.git`；旧仓库改名 `nest-origin` 并保持不变。
- 影响：禁止 force push；新仓库从当前 `main` 历史继续，阶段工作使用 `codex/` 分支。

## D011：Python 数据栈

- 状态：已确认到组件层
- 决策：Python 3.12、FastAPI、Pydantic Settings、SQLAlchemy 2.x async、asyncpg、Alembic、pytest；具体依赖精确版本在 P01 锁定。
- 影响：所有请求数据库操作必须使用请求级 async session 和明确事务；迁移不能由多 worker 启动时自动竞争执行。

## D012：支付事实优先于即时通知

- 状态：已确认
- 决策：支付宝通知必须验签、验订单/金额/商户并幂等事务落库；事务提交后才发 Socket.IO 事件，通知失败可补偿。
- 影响：不能在数据库事务中直接把一次 Socket emit 当作可靠交付；前端还需通过 API 查询确认最终状态。
