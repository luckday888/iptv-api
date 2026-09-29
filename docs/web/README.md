# Web 管理端设计文档

本目录包含 IPTV-API Web 管理端的设计文档。

| 文档 | 内容 |
|---|---|
| [PRD.md](PRD.md) | 产品需求文档：背景、用户场景、8 个页面功能需求、非功能需求、验收标准 |
| [SAD.md](SAD.md) | 系统架构设计：总体架构、路由共存、后端模块、后台任务模型、短轮询、前端结构、安全与构建 |
| [ASD.md](ASD.md) | API 接口文档：通用约定、各模块 REST 接口定义及与现有模块映射 |
| [DDD.md](DDD.md) | 数据库设计：复用的 SQLite 表结构、新增配置项、源文件格式、会话与一致性 |
| [DEPLOY.md](DEPLOY.md) | 部署手册：单镜像/双容器部署、环境变量、持久化、HTTPS、源码部署、升级与排障 |

## 关键结论
- 在现有 Flask + gunicorn（sync 单 worker）上扩展，不新增常驻进程；
- 管理端入口 `/admin`，API 前缀 `/api/admin`，与现有订阅接口零冲突；
- 前端 React 18 + Ant Design 5 + Vite；
- 实时更新采用短轮询（不引入 WebSocket/SSE）；
- 单密码登录 + 签名会话，新增 `admin_password` 等配置项；
- 业务逻辑全部复用现有 Python 模块。
