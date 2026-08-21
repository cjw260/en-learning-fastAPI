# P01：FastAPI 工程骨架与数据库基础

状态：`IN_PROGRESS`

## 启动条件

- P00 为 `COMPLETED` 且提交已推送。
- 用户在新的执行中明确启动 P01。
- 当前对话重新加载 `en-learning-backend-refactor` 并锁定 P01。

## 目标与外部效果

- Core API、AI API、worker 可独立启动和停止。
- 提供一致的配置、日志、错误和响应骨架。
- 空 PostgreSQL 可通过 Alembic 建表、降级、再次升级。
- 本阶段只有契约骨架和健康检查，不返回伪造业务结果。

## 实现步骤

1. 建立 `fastapi-backend/` 与 `pyproject.toml`，锁定 Python 3.12 及依赖，配置 pytest、lint、format、type-check。
2. 创建 `en_learning.api.main`、`en_learning.ai.main`、`en_learning.worker` 入口和共享包边界。
3. 用 Pydantic Settings 读取环境变量；提供不含秘密的 `.env.example`，验证缺失配置快速失败。
4. 使用 FastAPI lifespan 初始化/关闭数据库 engine、Redis、MinIO、HTTP 客户端；禁止 import 时连接外部服务。
5. 实现 request ID、结构化日志、统一成功 envelope、异常 handler、Pydantic 验证错误转换。
6. 建立 `/health/live` 与 `/health/ready`，区分进程存活和依赖就绪。
7. 将 Prisma 模型逐一映射为 SQLAlchemy 2.x 模型，明确 timezone、Decimal、JSON、枚举、cascade、索引和唯一约束。
8. 创建 Alembic 初始迁移；迁移由显式命令运行，不在 Uvicorn 多 worker 启动时自动执行。
9. 通过最小故障/重试验证选择 Redis worker 库并写入决策记录。
10. 建立 `/api/v1`、`/ai/v1` 路由模块骨架及 OpenAPI tag，不实现后续阶段业务。

## 验收标准

- [ ] 三类进程独立启动、停止和资源释放通过。
- [ ] live/ready 在依赖正常和异常时语义正确。
- [ ] 统一响应和验证错误有自动化契约测试。
- [ ] Alembic upgrade → downgrade → upgrade 通过。
- [ ] ORM 与批准 schema 的约束、索引、精度和关系一致。
- [ ] 缺失配置不泄露秘密，日志含 request ID 且无敏感值。
- [ ] pytest、lint、format check、type-check 全部通过。
- [ ] 无 P02 数据导入、P03 AI 或 P04+ 业务实现。

## 回退

独立目录可通过 revert 移除；NestJS、数据库生产实例和 Nginx 不受影响。
