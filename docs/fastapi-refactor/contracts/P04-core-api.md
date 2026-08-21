# P04 Core API 契约清单

基线：NestJS controller/service、`packages/common` 类型和 Vue/tracker 调用方。统一前缀保持 `/api/v1`，成功响应保持 `timestamp/path/message/code/success/data`；失败响应不含 `data`。

## 路由

| 方法 | 路径 | 身份 | 请求 | 成功 data | 主要失败 |
|---|---|---|---|---|---|
| POST | `/user/login` | 无 | `phone`, `password` | 用户公开字段 + `token.accessToken/refreshToken` | 401、422、503 |
| POST | `/user/register` | 无 | `name`, `phone`, `email?`, `password` | 用户公开字段 + token | 409、422、503 |
| POST | `/user/refresh-token` | refresh token body | `refreshToken` | 新 access/refresh token | 401、422、503 |
| POST | `/user/upload-avatar` | Bearer access | multipart `file` | `previewUrl`, `databaseUrl` | 401、413、422、503 |
| POST | `/user/update-user` | Bearer access | 既有用户可编辑字段；兼容前端附带只读用户字段并忽略 | 既有 update select 字段 | 401、409、422、503 |
| GET | `/course/list` | 无 | — | 课程数组；price 两位小数字符串 | 503 |
| GET | `/course/my` | Bearer access | — | 当前用户支付成功课程数组 | 401、503 |
| GET | `/word-book` | 无 | `page`, `pageSize`, `word?`, 八类 bool tag | `{total,list}` | 422、503 |
| GET | `/learn/word/{id}` | Bearer access | course id | 未掌握的前 10 个课程单词 | 401、403、422、503 |
| POST | `/learn/word/master` | Bearer access | `{wordIds}` | `{wordNumber}` | 401、403、422、503 |
| POST | `/tracker/uv` | 匿名；绑定用户时 Bearer | `anonymousId`, `userId?`, browser/os/device | visitor id 字符串 | 401、403、413、422、429、503 |
| POST | `/tracker/update-uv` | Bearer access | `visitorId`, `userId` | `true` | 401、403、404、413、422、429、503 |
| POST | `/tracker/performance` | 匿名 | Web Vitals 数值 | `true` | 404、413、422、429、503 |
| POST | `/tracker/pv` | 匿名 | visitor/url/referrer/path | `true` | 404、413、422、429、503 |
| POST | `/tracker/event` | 匿名 | visitor/event/payload/url | `true` | 404、413、422、429、503 |
| POST | `/tracker/error` | 匿名 | visitor/error/message/stack/url | `true` | 404、413、422、429、503 |

## 明确批准的安全差异

1. 旧 `ResponseService.error()` 会被全局 interceptor 包成 HTTP 200、`success: true`。P04 改为真实 4xx/5xx failure envelope；P06 必须统一前端错误展示。
2. `upload-avatar` 从无认证改为 Bearer access；对象键不再包含原始文件名，改为 `users/{jwt-user}/{uuid}.{safe-ext}`。
3. `tracker/update-uv` 必须认证，body `userId` 只能与 JWT 一致；`tracker/uv` 只有在有效 JWT 存在时才允许绑定用户。
4. 新注册密码存储为 versioned scrypt；旧明文/前端 MD5 值仅在首次成功登录时常量时间验证并立即升级。返回体永不包含密码或 refresh version。
5. refresh token 增加单调版本并在每次登录/刷新时轮换；旧 NestJS refresh token 缺少版本时按版本 0 处理，只能成功换取一次新 token 链。
6. WordBook 使用内部 `frqRank` 正数升序，null/空/非数值/0 稳定置尾；对外仍只返回旧 `frq` 字符串。
7. tracker 每条请求限制 64 KiB、按来源与端点限速，并在持久化前删除 token/password/cookie 等敏感 key、遮盖 token/邮箱/手机号和敏感 URL query。

P04 不包含 `/pay/**`、Socket.IO、任务生产/消费或生产 Nginx 切流。
