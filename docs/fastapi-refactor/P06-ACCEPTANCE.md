# P06 前端与全链路验收报告

状态：`PASS`

验收日期：2026-08-21（Asia/Shanghai）

## 结论

P06 的最小前端安全适配、契约回归、真实浏览器用户旅程、并发/延迟冒烟和资源稳定性检查均通过。测试只使用本机隔离 PostgreSQL、Redis、MinIO、生成的 RSA 密钥及确定性 LLM/支付宝/邮件替身；没有连接生产数据库、真实支付、真实邮件或生产凭证，也没有修改 Nginx、systemd、PM2 或服务器。

## 自动化与构建

| 门禁 | 结果 |
|---|---|
| Web 行为测试 | `9 passed`：refresh 成功/失败并发、支付状态去重/兼容、SSE 401/首帧后故障/首帧超时/总超时/取消 |
| Tracker 类型 | `pnpm --filter @en/tracker type-check` PASS |
| Web 类型与生产构建 | `pnpm --filter @en/web build` PASS；构建前顺序完成 tracker 声明、Vue 类型检查和 Vite build |
| Python 质量与回归 | uv lock 离线检查、Ruff format/lint、mypy 均 PASS；完整 pytest `81 passed` |

生产构建仍报告既有的 Three.js vendor chunk 约 789 kB（gzip 约 205 kB）和插件耗时提示；它不影响正确性，但应在未来独立性能优化中按真实首屏指标决定是否拆分。bundle 报告现只写入被忽略的 `dist/stats.html`，不污染工作区。

## 实际浏览器用户旅程

固定视口为 1440 × 900，前后使用同一现有 UI，不做布局重设计。浏览器连接本地 Core `:3000`、AI `:3001`、Web `:8080`、Redis `:56379`、PostgreSQL `:55432` 与 MinIO `:59000`。

| 旅程 | 结果与证据 |
|---|---|
| 注册/登录/错误/恢复 | 注册 P06 本地用户成功；错误密码显示“手机号或密码不正确”；退出后正确凭据恢复登录 |
| 资料与头像 | 上传现有 JPEG，保存邮箱、地址与签名，服务端 upload/update 均 200，页面显示“保存成功” |
| Tracker | uv、pv、event、error 及登录后的 Bearer `update-uv` 均有 200；失败采用非阻塞重试边界 |
| 词库 | 高考标签 + `browser-word` 搜索得到 15 条；第 1 页 12 条、第 2 页 `13–15`，分页稳定 |
| 课程与支付 | 课程列表展示 8 门；创建高考课程订单时 access token 过期，日志为 pay/create 401 → 唯一 refresh 200 → 原请求 200；本地网关提交 RSA2 签名回调，支付状态轮询/API 与 Socket 最终切换“我的课程” |
| 学习与掌握 | 逐字完成 `browser-word-01` 至 `browser-word-10`，保存后顶部掌握数从 0 变 10，下一组为 11–15 |
| AI 普通/深度 | 普通模式返回“普通模式回答”；深度模式按 reasoning“深度分析”后输出“深度模式回答” |
| AI 历史/隔离 | 切到英语大师为空；切回智能助手恢复上述历史，角色隔离通过 |
| AI 加载/取消 | 延迟替身时出现“AI 正在思考…”与“停止”；点击后输入恢复且显示“已停止生成”，没有重复回复 |
| Socket 重连 | token refresh 后同一客户端携新 token 重连；支付后重连/轮询都从 API 确认最终购买事实 |
| 资源与视觉 | `/en/` 模型资源正常加载；组件卸载会取消动画并 dispose Three.js renderer/control/model，导航无持续资源增长 |

Vite 首次开发依赖优化曾触发一次动态模块重载，依赖预热后完整旅程无应用运行时错误；这是开发服务器行为，不存在于已通过的生产构建中。

## 契约结果

路径、方法、主要请求字段、envelope、AI reasoning/chat 分片、Socket 事件名和课程/学习/词库返回形状无未批准差异。全部安全差异与 NestJS 回退兼容方式见 `contracts/P06-frontend-compatibility.md`。

## 并发、延迟与资源

本阶段锁定的本机冒烟基线为：每个端点 200 个请求、并发 20、错误数 0、P95 不超过 500 ms。第二次稳定运行结果：

| 端点 | 错误 | P50 | P95 | 最大值 |
|---|---:|---:|---:|---:|
| `GET /api/v1/course/list` | 0 | 95.99 ms | 275.67 ms | 371.81 ms |
| `GET /api/v1/word-book?page=1&pageSize=12` | 0 | 99.97 ms | 302.12 ms | 497.32 ms |
| `GET /ai/v1/prompt/list` | 0 | 72.61 ms | 261.83 ms | 525.47 ms |

资源快照采用“运行前 → 第一次 → 同参数第二次”：PostgreSQL 当前库连接 `6 → 8 → 8`，Redis connected clients `9 → 9 → 9`，Core 进程文件描述符 `89 → 91 → 91`。第一次仅扩展到配置允许的持久连接池，重复运行不再增长，未见持续泄漏。该冒烟不是生产容量证明。

## P07 初始容量建议

以下只作为 P07 旁路实测起点，不是生产变更授权：

- Core API 从 2 个 Uvicorn worker 起步，确认 CPU/RAM 后最多先扩到 4；AI API 从 2 个 worker 起步；worker 与 scheduler 各 1 个进程，并依靠 durable job/分布式锁避免重复事实。
- 当前每进程数据库池为 `5 + 5 overflow`。P07 必须以 `所有 Core + AI + worker 的最坏连接数 < PostgreSQL max_connections - 运维保留` 重新核算；不得直接把 worker 数和池大小同时放大。
- 保持 HTTP 10 秒、健康检查 2 秒、LLM 连接 5 秒/首 token 30 秒/总时长 120 秒；浏览器首帧 35 秒/总时长 130 秒，为代理和清理留余量。
- Socket 使用 WebSocket + Redis manager；Nginx 必须正确升级连接。SSE 必须关闭代理缓冲并让 read timeout 大于 130 秒。Redis 客户端数、数据库池等待、SSE 活跃数、Socket 连接数、错误率与 P95 都应进入灰度阈值。

## 已知非阻塞风险

1. 本阶段只验证生成密钥的本地支付宝替身、确定性 LLM 与假邮件，不代表真实供应商配额、网络抖动或生产证书已通过。
2. Three.js vendor chunk 超过构建警告阈值；当前 gzip 体积可控，但需用生产真实网络监测首屏后再决定拆包。
3. 本机并发冒烟不等价于长期 soak 或生产峰值；P07 旁路端口必须重新执行长连接、真实资源和回退阈值观察。

## P07 上线前只读清单

- [ ] 用户在新的执行中明确授权 P07，并重新加载必需 skill。
- [ ] 获取生产 CPU/RAM、PostgreSQL `max_connections`、Redis `maxclients` 与当前峰值，锁定 worker/池预算。
- [ ] 备份 PostgreSQL、Nginx、PM2、环境和部署脚本，并实际验证恢复。
- [ ] 为 Core、AI、worker、scheduler 准备非 root systemd unit、环境文件权限、日志轮转与停止超时。
- [ ] 在旁路端口执行 migration check、health、课程/词库、SSE、Socket、多标签页、worker 重启和资源 soak。
- [ ] 配置 Nginx SSE 无缓冲、WebSocket upgrade、超时、分阶段 `/ai/` → `/api/` upstream 与一键回退。
- [ ] 锁定错误率/P95/连接数/支付/任务阈值、观察窗口和操作者记录。
- [ ] 只有用户另行确认后才做真实小额支付、停止旧 PM2 或处置旧代码；本阶段没有执行任何一项。
