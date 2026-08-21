# P02：开发数据初始化

状态：`IN_PROGRESS`

## 启动条件

P01 完成并推送；新的执行重新加载 skill；阶段锁为 P02。

## 目标与外部效果

在没有本地生产数据的电脑上，用一条受控命令重建数据库结构、ECDICT WordBook、八门课程和八张课程图片；重复运行结果一致。

## 实现步骤

1. 固定 `skywind3000/ECDICT` 的 commit/tag、许可证和源文件 SHA-256；源版本变更必须显式更新决策。
2. 为 ECDICT 建立字段映射：word、phonetic、definition、translation、pos、collins、oxford、tag、bnc、frq、exchange 和考试标签。
3. 流式读取并批量 upsert，处理 BOM/编码、空值、超长字段、坏行；产生拒绝行报告。
4. 将 `frq` 规范为可排序数值；正数升序，null/空/非数值/0 置后，再用稳定次序消除分页抖动。
5. 将 `server/prisma/seed.ts` 中八门课程转换为按 `value` 幂等 upsert，保持价格精度和 URL 规则。
6. 检查/创建 MinIO `course` bucket 与公开读策略，按正确 MIME 上传八张现有 PNG；对象键稳定。
7. 编排 `migrate -> import words -> seed courses/assets -> verify`，任何失败返回非零状态。
8. 输出来源、校验、数量、跳过/失败、耗时和环境标识，不输出凭证。

## 验收标准

- [x] 空库一条命令完成全部基础数据初始化。
- [x] 来源版本、许可证和 SHA-256 可追溯。
- [x] 连续执行两次无重复记录或多余对象。
- [x] 字段映射、坏行、批次失败和恢复有测试。
- [x] 八门课程/八张图片完整且可通过对象 HEAD 验证。
- [x] `frq` 排序和分页边界满足决策 D007。
- [x] 不生成用户、学习、支付、埋点或聊天数据。
- [x] 初始化报告准确，失败不会宣称成功。

## 回退

仅允许按明确开发环境和导入批次清理；不对未知或生产数据库执行全量删除。

## 已锁定实现（2026-08-21）

- 唯一入口：`uv run en-learning-bootstrap`；生产环境在执行迁移前硬拒绝。
- ECDICT：标签 `1.0.28`，提交 `8defb761f7c7ad1818ca94290a1844d7b33d6b23`，SHA-256 `d0ce61e560b50d9905d20de3173aa3ca80950ce235bedd21c53e025cf9f38cb0`，共 770,611 条。
- 数据约束：`WordBook.word` 和 `Course.value` 唯一；`frqRank` 仅存正整数，稳定排序为 `frqRank ASC NULLS LAST, word ASC, id ASC`。
- 批次恢复：默认每 1,000 条单独提交；失败报告记录已提交批次，重跑走 upsert/skip，不需要全表回滚。
- 对象存储：固定 `course/{value}.png`，设置公开只读策略、`image/png` 和源文件 SHA-256 metadata；每次运行都做公开 HEAD 验证。
- 报告：成功/失败、环境、来源/许可证/校验值、导入/更新/跳过/拒绝、数据库数量、课程/对象数量、保护表前后计数、耗时；不包含凭证。

## 全量验收证据

- 临时 PostgreSQL 与 MinIO 空环境第一次执行：770,611 词插入、0 拒绝、8 课程插入、8 对象上传并公开 HEAD 通过；耗时 131.207 秒。
- 同一命令第二次执行：770,611 词 skip、8 课程 skip、8 对象 skip，数据库仍为 770,611 词/8 课程/8 对象；耗时 22.836 秒。
- 两次执行的用户、学习、支付、埋点相关表前后均为 0；固定源大小和 SHA-256 均验证通过。
