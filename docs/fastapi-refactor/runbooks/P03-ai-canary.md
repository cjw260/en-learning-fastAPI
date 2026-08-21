# P03 AI-only 灰度与回退准备

状态：`PREPARED_ONLY`。本文件不授权部署；只有 P07 或用户另行明确批准生产操作后才可执行。

## 适用边界

- 只切换 `/ai/` 到 FastAPI AI API，Core `/api/`、Socket.IO、支付和 worker 保持 NestJS。
- FastAPI AI 旁路监听建议为 `127.0.0.1:8001`；旧 NestJS AI `127.0.0.1:3001` 必须保持运行。
- 生产库首次接入 Alembic 前必须按 D015 比对现有 schema 并受控 stamp；禁止直接对既有生产库运行空库初始迁移。
- 环境文件必须由最小权限 systemd unit 读取，且 `SECRET_KEY` 与现有 Core API 一致；禁止把密钥写入 Nginx、仓库或命令历史。

## 切换前检查

1. 备份并验证当前 Nginx 配置可恢复，记录旧 AI upstream 为 `127.0.0.1:3001`。
2. 在旁路端口启动 FastAPI AI，确认 `/health/live` 为 200，`/health/ready` 的 PostgreSQL、Redis、MinIO 均为 up。
3. 使用测试账号验证带 access token 的 prompt、普通 chat、深度 chat、history；确认无 token 为 401、跨用户 `userId` 为 403。
4. 确认 `AIChatThread`/`AIChatMessage` 可写、Redis lease 可释放、日志中没有提示词或凭证。
5. 保存变更前 15 分钟错误率、P95、首 token 延迟、SSE 中断率、PostgreSQL/Redis 连接和 AI 进程资源基线。

## 待授权的 Nginx 语义

现有 location 结构必须按服务器实际配置审查后再编辑；AI upstream 需要保留以下语义：

```nginx
location /ai/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 180s;
    proxy_send_timeout 180s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

应用前必须运行 `nginx -t`；只有检查成功才能 reload。不要停止旧 PM2 AI 服务。

## 观察与停止条件

- 先用受控测试账号验证，再逐步放量；每一步记录时间、比例、错误率、P95、首 token、SSE 中断和依赖健康。
- 任一出现持续 5xx/401 异常升高、SSE reasoning/chat 顺序破坏、历史越权或混写、数据库迁移异常、Redis 锁异常、凭证泄露迹象时立即停止放量并回退。
- 具体百分比、观察窗口和阈值必须在 P07 根据上线前基线锁定，P03 不预设生产数字。

## 回退

1. 将 `/ai/` upstream 恢复为 `127.0.0.1:3001`，运行 `nginx -t` 后 reload。
2. 验证旧 NestJS prompt/chat/history、AI SSE 和前端页面恢复；Core API 不应受到切换影响。
3. 保留 P03 新历史表和故障窗口日志用于审计，不做盲目数据库 downgrade，不删除用户在 FastAPI 窗口产生的新历史。
4. 停止 FastAPI AI 接收新请求前先完成连接排空；旧 NestJS 稳定后再保存证据和复盘。

本回退不会把 FastAPI 窗口产生的新历史复制回旧 LangGraph，因此旧服务恢复后这部分历史暂时不可见；这是 D008 已接受的历史边界，不影响 Core、支付或学习数据。
