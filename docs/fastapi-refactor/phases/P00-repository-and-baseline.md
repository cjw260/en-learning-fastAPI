# P00：仓库、计划与旧系统基线

状态：`COMPLETED`

当前阶段锁：`P00`

视觉验收：N/A（纯文档/仓库治理阶段）

## 目标

建立新仓库边界、唯一权威计划、进度台账和旧 NestJS 兼容基线，使任何新对话都能从文件恢复准确状态。

## 允许范围

- 根 `AGENTS.md`。
- `docs/fastapi-refactor/**`。
- Git 远端名称/URL、P00 阶段分支、P00 文档提交和推送。

禁止 FastAPI 运行时代码、依赖安装、数据库写入和生产操作。

## 执行步骤

1. 加载 skill，验证仓库标识和 Git 基线。
2. 读取 controller/service、共享类型、Prisma schema/seed、前端 API 和部署文件。
3. 建立权威计划、决策、基线、进度和 P00-P07 阶段执行卡。
4. 检查现有构建和测试能力，如实记录缺失项。
5. 旧远端改名 `nest-origin`，新 FastAPI 仓库成为 `origin`，无 force push 地继承 `main` 历史。
6. 检查文档链接、敏感内容、阶段一致性、空白错误和最终变更范围。
7. 创建 `codex/p00-repository-baseline`，只提交 P00 文档并推送。
8. 将所有证据回填 `PROGRESS.md`，完成后结束本次执行。

## 验收检查表

| 标准 | 命令/方法 | 证据 | 状态 |
|---|---|---|---|
| 当前任务加载 skill | 读取 SKILL.md | 见 PROGRESS | PASS |
| 仓库标识正确 | 路径检查 | 四项全部 OK | PASS |
| 权威计划完整 | 人工审阅 AGENTS | 已包含 P00-P07 | PASS |
| 阶段文档齐全 | 文件清单检查 | P00-P07 共八个文件已创建 | PASS |
| 旧系统基线完整 | controller/schema/frontend/deploy 对照 | `LEGACY_BASELINE.md` 已覆盖 | PASS |
| 旧远端保留 | `git remote -v` | `nest-origin` 指向旧仓库 | PASS |
| 新仓库继承历史 | 比较 main commit | 两个远端 main 均为 `d406e118...` | PASS |
| 无秘密和越界文件 | status/diff/敏感模式检查 | 只暂存 13 个 P00 文档；常见密钥检查通过 | PASS |
| 文档质量通过 | 链接/格式/空白检查 | 路径存在；diff check、空白和冲突标记检查通过 | PASS |
| 提交推送成功 | commit/branch/remote 检查 | `984d60e` 已推送到 `origin/codex/p00-repository-baseline` | PASS |
| 未进入 P01 | 最终文件范围 | `fastapi-backend/` 不存在，无运行时代码 | PASS |

## 回退

- 文档用普通 revert 回退。
- 若需要恢复本地默认远端：保留新远端为其他名称，再将 `nest-origin` 改回 `origin`。
- 不删除、不 force push 旧仓库或新仓库的历史。

## 完成记录

- 完成日期：2026-08-21
- 主提交：`984d60e`
- 分支：`codex/p00-repository-baseline`
- 新远端：`origin -> https://github.com/cjw260/en-learning-fastAPI.git`
- 旧远端：`nest-origin -> https://github.com/cjw260/en-learning.git`
- 审查：PASS
- 下一步：结束当前执行；P01 必须由用户在新执行中启动并重新加载 skill。
