# FastAPI 后端重构文档入口

本目录用于让新的 Codex 对话在没有聊天上下文时，仍能准确恢复 en-learning 后端重构进度。

## 必读顺序

1. 仓库根目录 [`AGENTS.md`](../../AGENTS.md)：唯一权威计划、执行规则、当前阶段和验收门禁。
2. [`PROGRESS.md`](PROGRESS.md)：当前阶段逐项证据、阻塞点和下一动作。
3. 当前阶段文件：位于 [`phases/`](phases/)。
4. [`LEGACY_BASELINE.md`](LEGACY_BASELINE.md)：NestJS API、数据与部署兼容基线。
5. [`DECISIONS.md`](DECISIONS.md)：已经锁定的架构和产品决策。

如果上述文档与聊天描述冲突，以根目录 `AGENTS.md` 为准；不得跳过未完成阶段。

## 强制执行口令

开始、继续、修复、验收、审查、提交或推送任一阶段时：

```text
必须在当前对话重新加载 en-learning-backend-refactor skill。
一次执行只能处理一个阶段。
前一阶段全部验收、审查、复测和推送完成后，本次执行必须结束。
```

上一对话中的 skill 加载记录不能复用。未加载时将阶段标记为 `BLOCKED`，禁止修改实现。

## 文档目录

| 文件 | 用途 |
|---|---|
| `PROGRESS.md` | 当前状态、验收证据、Git 信息、阻塞与下一动作 |
| `DECISIONS.md` | 重要决策、理由、影响和变更历史 |
| `LEGACY_BASELINE.md` | 旧系统 HTTP/SSE/Socket.IO/数据/部署基线 |
| `phases/P00-repository-and-baseline.md` | 仓库、计划与基线 |
| `phases/P01-foundation-and-database.md` | FastAPI 工程骨架与数据库基础 |
| `phases/P02-data-bootstrap.md` | ECDICT 与课程数据初始化 |
| `phases/P03-ai-service.md` | AI API、SSE 与聊天历史 |
| `phases/P04-core-business-api.md` | 用户、词库、课程、学习与埋点 |
| `phases/P05-payment-socket-worker.md` | 支付、Socket.IO 与后台任务 |
| `phases/P06-frontend-and-verification.md` | 前端适配与全链路验收 |
| `phases/P07-rollout-and-cleanup.md` | 灰度上线、回退和旧服务处置 |

## 更新纪律

- 阶段开始：更新 skill 加载、Git 基线、阶段锁、范围和风险。
- 实现期间：验收项必须记录验证方法、证据与状态，不能只打勾。
- 阶段结束：记录最终审查、命令结果、提交哈希、分支和远端推送结果。
- 遇到环境缺失：保留真实失败证据并标记 `BLOCKED` 或 `IN_PROGRESS`，禁止伪造成功。
- 计划变更：先更新根 `AGENTS.md`，再同步本目录；不得只改阶段文件绕过权威计划。
