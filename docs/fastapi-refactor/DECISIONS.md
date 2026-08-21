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

## D013：P01 锁定 Taskiq Redis Stream worker

- 状态：已确认
- 决策：Python worker 使用 `taskiq==0.12.4` 与 `taskiq-redis==1.2.3`；broker 采用 `RedisStreamBroker`，scheduler 采用独立进程与 `ListRedisScheduleSource`。
- 原因：Redis Stream broker 提供消费组和消息确认，能避免 Pub/Sub 与 List broker 在 worker 崩溃时直接丢失已取消息；Taskiq 同时支持 async task、独立 scheduler 和信号关停。
- 重试：默认接入 `SimpleRetryMiddleware`，只有任务显式声明 `retry_on_error` 时才重试；P05 必须为外部副作用任务锁定最大次数、退避、超时和失败记录。
- 幂等：队列确认和重试不等于业务幂等。P05 必须为支付、邮件与调度任务设计稳定任务键、数据库唯一约束或分布式锁，不能依赖进程内状态。
- 失败队列：Taskiq/Redis Stream 不自动满足项目的死信审计要求；P05 必须实现明确失败记录与可控重放，未完成前不承诺等价替代 BullMQ 全部行为。
- 关停：HTTP 与 worker 分别管理资源；worker 通过 Taskiq startup/shutdown hook 创建并关闭数据库、Redis、MinIO、HTTP/LLM 客户端，scheduler 独立运行。

## D014：保持 Prisma PostgreSQL 物理 schema

- 状态：已确认
- 决策：P01 的 SQLAlchemy/Alembic 保留现有大小写表名、camelCase 列名、索引/外键名称、`DECIMAL(65,30)`、`JSONB`、`TradeStatus` 原生枚举和 `TIMESTAMP(3) WITHOUT TIME ZONE`。
- 时间语义：旧 Prisma 物理列无时区。为避免灰度期两套 ORM 争用 schema，P01 不改列型；应用层统一按 UTC 生成 naive datetime。改为 `TIMESTAMPTZ` 必须另行设计数据转换与双后端兼容方案。
- 影响：Python 属性使用 snake_case，但显式映射旧物理名称；所有外键保持 `ON DELETE/UPDATE CASCADE`，请求会话不隐式提交，业务事务由后续阶段显式划定。

## D015：Alembic 初始迁移仅用于空库

- 状态：已确认
- 决策：P01 初始迁移可对空 PostgreSQL 完整建表/降级/再升级；应用启动绝不自动执行迁移。
- 生产约束：现有生产库在 P07 前不得直接运行该初始迁移。P07 必须先比对实际 schema 与 P01 metadata，再通过受控 `stamp`/基线流程接管迁移历史，避免 Alembic 与 Prisma 同时创建既有对象。

## D016：P02 固定 ECDICT 1.0.28 基础 CSV

- 状态：已确认
- 决策：开发 WordBook 使用 `skywind3000/ECDICT` 标签 `1.0.28`、提交 `8defb761f7c7ad1818ca94290a1844d7b33d6b23` 下的 `ecdict.csv` 基础版（65,936,699 bytes，770,611 条记录）。
- 完整性：源文件 SHA-256 为 `d0ce61e560b50d9905d20de3173aa3ca80950ce235bedd21c53e025cf9f38cb0`；运行前必须同时验证大小和 SHA-256，禁止接受同名但内容变化的文件。
- 许可证：固定提交使用 MIT License，Copyright (c) 2017 Linwei；项目保留 `resources/ECDICT-LICENSE.txt` 和来源清单。
- 映射：保留对外 `frq` 字符串，新增内部 nullable `frqRank`；只有正整数进入 rank，null/空/非数值/0 统一为 null 并按 `frqRank, word, id` 稳定排序。`detail`、`audio` 当前模型无对应字段，P02 明确校验但不导入。
- 幂等：WordBook 以 `word`、Course 以 `value` 建立唯一键；ID 从自然键确定性生成。词库每 1,000 条独立事务提交，失败报告已提交批次数，重跑从头 upsert 即可恢复。

## D017：P03 使用显式 DeepSeek 流式适配层

- 状态：已确认
- 决策：AI HTTP 进程通过独立 `DeepSeekClient` 调用 DeepSeek 的 OpenAI-compatible SSE 接口；P03 不把 LangChain/LangGraph 引入请求主路径，也不在框架对象中隐藏连接、重试或事务边界。
- 模型：普通模式使用 `deepseek-chat`，深度思考使用 `deepseek-reasoner`，均可由环境变量覆盖；Bocha 搜索通过独立适配器提供有界、不可信的参考上下文。
- 超时与重试：分别限制连接、首 token 和总时长；只允许在尚未向客户端发送模型输出前有限重试，首分片后禁止自动重试，避免重复内容。客户端断开时关闭上游 async iterator。
- SSE：保持旧前端的 `reasoning`/`chat` JSON 载荷，不新增需要前端解析的业务事件；使用 SSE 注释心跳、`Cache-Control: no-cache, no-transform` 和 `X-Accel-Buffering: no`。
- 可观测性：只记录哈希用户引用、角色、功能开关、分片/字符数、上游返回的 token 用量、延迟和失败类型；不记录完整提示词、Bearer token、DeepSeek/Bocha 密钥或上游错误正文。

## D018：P03 JWT 身份优先与独立新历史

- 状态：已确认
- 决策：`prompt/list`、`chat`、`chat/history` 只接受使用既有 `SECRET_KEY` 签发的 HS256 access token；固定校验算法、签名、`exp`、可选 `nbf`、`tokenType=access` 和非空 `userId`。
- 兼容性：旧前端仍发送 body/query `userId`，P03 暂时保留该字段，但必须与 JWT 用户一致；不一致返回 403，字段本身不参与身份确定。前端 Axios 和 SSE 请求补充 Bearer header。
- 历史：新建 `AIChatThread`/`AIChatMessage`，以 user+role 唯一隔离并保留消息顺序、reasoning 和重启恢复能力；按 D008 不读取或转换旧 LangGraph checkpoint，首次访问空数组是预期结果。
- 并发：同一 user+role 在 Redis 中使用带随机 token 和原子 compare-delete 的短租约串行生成；Redis 不可用时拒绝开始聊天，避免无保护的并发写入。

## D019：P04 密码、refresh 轮换与业务错误语义

- 状态：已批准，2026-08-21。
- 密码：新注册值使用 versioned scrypt（独立随机盐）存储；兼容旧库时，仅在首次成功登录中常量时间校验旧值并立即升级。密码和内部 refresh 版本永不出现在 API 响应或日志。
- refresh：`User.refreshTokenVersion` 从 0 开始；登录和每次 refresh 在行锁事务中递增，token 携带版本。旧 NestJS token 未携带版本时解释为 0，因此同一用户的旧 refresh 链只能有一次迁移机会；并发重放只有一个成功。
- 错误：旧 `ResponseService.error()` 被 interceptor 包成 HTTP 200/`success:true` 是缺陷，不作为兼容目标。P04 依计划改用 401/403/404/409/413/422/429/503 failure envelope，P06 负责调用方错误展示适配。
- 身份：头像、学习和用户更新只接受 JWT 当前用户；tracker 用户绑定也必须认证且 body `userId` 与 JWT 一致。
