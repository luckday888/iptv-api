# IPTV-API Web 管理端 系统架构设计文档（SAD）

版本：v1.0
日期：2026-09-29
配套文档：[PRD.md](PRD.md)、[ASD.md](ASD.md)、[DDD.md](DDD.md)

## 1. 架构目标与原则

1. **不影响现有服务**：订阅结果服务（m3u/txt/epg/hls_proxy）行为保持不变；
2. **复用业务逻辑**：Web 端是现有 Python 业务模块的薄封装，不重复实现采集、测速、转推逻辑；
3. **单进程内集成**：在现有 Flask 应用上扩展管理 API 与静态资源，不新增常驻进程；
4. **前后端分离构建**：前端独立工程，构建产物为静态文件，由 Flask/nginx 托管；
5. **同步阻塞操作异步化**：Flask 同步框架通过后台线程 + asyncio 子循环执行更新与频道操作，结果经 WebSocket 推送。

## 2. 总体架构

```
浏览器（React SPA）
   │  HTTPS/HTTP（短轮询）
   ▼
nginx（容器内，:8080）
   │  /            订阅结果（反代到 Flask 或直接读文件）
   │  /m3u /txt /epg /hls_proxy ...（现有路由）
   │  /admin       管理端静态资源（SPA）
   │  /api/admin/* 管理 API（反代到 Flask）
   ▼
Flask + gunicorn（127.0.0.1:5180，单 worker，sync）
   ├── 现有订阅 Blueprint（service/app.py 路由，保持不变）
   ├── service/web/ 管理端后端（新增）
   │     ├── auth        登录、会话、鉴权装饰器
   │     ├── api         REST Blueprint（按模块拆分）
   │     ├── tasks       后台任务编排（更新/频道操作）
   │     └── files       源文件读写解析
   └── 现有业务模块（被复用）
         ├── main.UpdateSource           更新流程
         ├── utils.channel_repository    频道/结果/运行/操作 持久化
         ├── utils.channel_operations    重测/截图
         ├── utils.config                配置读写与校验
         ├── utils.user_actions          源文件增删（白/黑名单、手动频道）
         ├── utils.rtmp_stats            RTMP 快照采集
         └── service.rtmp                RTMP 控制
   ▼
SQLite（output/data/channel_results.db、rtmp.db） + config/ 文件 + output/ 文件
```

## 3. 部署形态与路由共存

### 3.1 路径划分
| 路径 | 归属 | 说明 |
|---|---|---|
| `/`、`/m3u`、`/txt`、`/ipv4`、`/ipv6`、`/content`、`/epg/*`、`/log/*`、`/hls_proxy/*` | 现有订阅服务 | 行为不变，**无需登录** |
| `/admin`、`/admin/assets/*` | 管理端 SPA | 静态资源；未登录由前端路由跳 `/admin/login` |
| `/api/admin/*` | 管理 REST API | 需登录（登录接口除外） |

选择 `/admin` 前缀的原因：现有 `/` 已用于订阅结果，独立前缀零冲突、零侵入。

### 3.2 两种部署模式
- **Docker 模式（推荐）**：nginx 托管 SPA 静态资源并反代 `/api/admin`、`/ws` 到 Flask；
- **裸 Python 模式**：Flask 直接托管 SPA 与 API（`service/app.py` 以 Flask 开发/生产方式运行）。

后端通过统一的静态资源与 API 注册同时支持两种模式，差异仅在 nginx 是否在前面。

## 4. 后端设计（service/web/）

### 4.1 模块划分
```
service/web/
├── __init__.py
├── extension.py          # 向现有 Flask app 注册 web 相关 Blueprint/资源
├── auth/
│   ├── __init__.py
│   ├── session.py        # 会话签发/校验（itsdangerous 签名）
│   └── decorators.py     # @admin_required / ws 鉴权
├── api/
│   ├── __init__.py       # api Blueprint 汇总
│   ├── auth_api.py       # 登录/登出/当前会话
│   ├── dashboard_api.py  # 状态指标、运行状态
│   ├── update_api.py     # 更新控制：run/pause/resume/cancel
│   ├── channels_api.py   # 分类、频道、结果、重测、截图、输出选择
│   ├── sources_api.py    # 7 类源文件读写、原始文本、导入导出
│   ├── rtmp_api.py       # RTMP 状态、频道选择、转推控制
│   ├── logs_api.py       # 日志读取/清空/导出
│   ├── tasks_api.py      # 运行历史 + 操作历史
│   ├── settings_api.py   # 配置元数据、读取、保存
│   └── about_api.py      # 版本、更新检查、changelog
├── tasks/
│   ├── __init__.py
│   ├── update_runner.py  # 更新任务执行（线程 + asyncio）
│   └── ops_runner.py     # 频道操作执行（重测/截图）
└── files/
    ├── __init__.py
    └── source_files.py   # 源文件路径解析、读写、解析/序列化
```

### 4.2 认证与会话
- 密码来源：新增配置项 `admin_password`；首次启动若为空，自动生成随机密码并写入配置 + 输出到启动日志（仅首次），强制登录后提示修改；
- 会话：使用 `itsdangerous.TimestampSigner`（Flask 依赖链已含）签名，载荷含过期时间；通过 HttpOnly Cookie 传递（SameSite=Lax）；
- 防暴力破解：内存中按 IP 记录失败计数，超限短时拒绝（429）。

### 4.3 后台任务执行模型

Flask 为同步框架，而更新/重测是 asyncio 协程，采用线程内独立事件循环：

```
REST 请求（更新控制）
   │  向单例 UpdateTaskManager 下发指令
   ▼
UpdateTaskManager（进程内单例，线程安全）
   ├── 工作线程：asyncio.new_event_loop
   │     └── UpdateSource.run_once(progress_callback, event_callback)
   ├── 控制方法：start / pause / resume / cancel（线程安全）
   └── 进度回调 → 写入 run_state + 更新内存状态快照（供短轮询读取）
```

要点：
- **单例、互斥**：同一时刻只允许一个完整更新任务，重复 start 返回 409；
- **复用回调**：`run_once` 已提供 `progress(title, percent, finished, url, now)` 与事件回调，回调内同时持久化到现有 `run_state.json` 并更新内存快照，保证刷新页面后状态不丢；
- 频道操作（重测/截图）复用桌面端 `ChannelOperations`，同样在工作线程协程中执行，进度由接口轮询读取、完成后返回/通知；
- gunicorn 单 worker 保证单例有效；启动时如检测到已有更新在跑（run_state），接管其状态。

### 4.4 实时性方案：短轮询

受限于 gunicorn **sync worker、单 worker**，不引入 WebSocket/SSE 长连接（会占死唯一 worker），改用短轮询：

| 数据 | 轮询接口 | 间隔 |
|---|---|---|
| 更新状态/进度 | `GET /api/admin/update/progress` | 约 1s（运行中） |
| 仪表盘指标 | `GET /api/admin/dashboard/metrics` | 约 5s |
| RTMP 快照/带宽 | `GET /api/admin/rtmp/runtime` | 约 2s |
| 日志增量 | `GET /api/admin/logs/<kind>`（带 offset） | 约 1.5s |
| 任务历史 | `GET /api/admin/tasks` | 约 3s |

- 任务在后台线程运行，轮询仅读取 `UpdateTaskManager` 维护的状态快照，不阻塞任务；
- 页面不可见（`visibilitychange`）时暂停轮询，重新可见立即拉取；
- 与桌面端定时刷新节奏一致，零新依赖、零 worker 配置变更。

### 4.5 源文件处理
- 路径解析：模板用 `config.source_file`，其余用 `constants` 中既有路径；
- 读写：统一在 `files/source_files.py`，提供 `read_raw / write_raw / parse / serialize`；
- 解析/序列化复用桌面端 `SourceEditor` 中已有的行解析规则（注释保留、分组、白名单规则），将纯函数逻辑从 UI 文件中抽取为可复用工具（仅抽取，不改规则）；
- 写入走临时文件 + 原子替换，失败回滚并返回错误信息。

## 5. 前端设计

### 5.1 技术栈
| 项 | 选型 |
|---|---|
| 框架 | React 18 |
| UI 组件库 | Ant Design 5 |
| 构建 | Vite 5 |
| 路由 | React Router 6（basename `/admin`） |
| 数据请求 | fetch 封装 + TanStack Query（缓存/刷新） |
| 状态 | Zustand（运行状态等全局轻状态） |
| 图表 | @ant-design/plots（带宽曲线） |
| 国际化 | i18next，复用现有 locales 资源转换 |
| 实时数据 | 短轮询封装（可配置间隔，页面不可见自动暂停） |

### 5.2 目录结构（web_admin/）
```
web_admin/
├── package.json            # 依赖安装于本目录（node_modules）
├── vite.config.js          # base=/admin/，dev 代理 /api、/ws
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx             # 路由 + 布局 + 鉴权守卫
    ├── api/                # 接口封装（按模块）
    ├── hooks/              # 轮询 hooks 等
    ├── components/         # 通用组件（台标、健康标签、播放器等）
    ├── layouts/            # 登录布局、管理布局（侧边导航）
    ├── pages/
    │     ├── login/
    │     ├── dashboard/
    │     ├── channels/
    │     ├── sources/
    │     ├── rtmp/
    │     ├── logs/
    │     ├── tasks/
    │     ├── settings/
    │     └── about/
    ├── hooks/
    ├── i18n/
    └── utils/
```

### 5.3 导航与路由
左侧导航对齐桌面端：仪表盘、频道中心、订阅源、播放转推、日志、任务历史；底部：设置、关于。未匹配路由重定向仪表盘。路由守卫校验登录态，401 清除会话跳登录。

### 5.4 关键交互
- **仪表盘**：页面加载拉当前 run_state 与指标；定时轮询更新进度与状态；按钮随状态切换（运行 → 暂停/取消，空闲 → 执行）；
- **频道中心**：左侧分类树 + 主表 + 结果抽屉（Drawer/DrawerPanel）；表格分页 + 虚拟滚动；重测/截图为异步任务，进度条 + 完成通知；
- **订阅源**：Tabs + 表格/文本编辑器双模式（a-descriptions / a-table + a-textarea）；脏检查离开提示；
- **播放转推**：选择弹窗（Transfer/Modal+Table）、转推表、实时曲线图（轮询）；
- **日志**：下拉选类型 + 搜索 + 自动滚动（`a-typography-text`/虚拟列表），增量轮询；
- **设置**：按值类型渲染表单项，高级项折叠，只读项禁用并显示环境变量提示。

## 6. 数据流（关键链路）

### 6.1 手动更新
```
点击执行 → POST /api/admin/update/run
  → UpdateTaskManager.start()（409 if running）
  → 工作线程 run_once
      progress 回调 → run_state.json + 更新内存快照
  → 完成 → channel_repository.finish_run，状态快照置 idle
前端约 1s 轮询 /update/progress 实时反映进度；任务历史出现新记录。
```

### 6.2 频道重测
```
POST /api/admin/channels/<key>/retest
  → ops_runner 调 ChannelOperations.retest_channel
  → 轮询进度 → 结果落 channel_results.db
  → GET 频道结果反映新测速数据
```

### 6.3 源文件编辑保存
```
GET /api/admin/sources/<kind> → 结构化行 + 原始文本
前端编辑
POST /api/admin/sources/<kind>（内容）
  → 校验 → 原子写文件 → 返回成功/错误
```

## 7. 错误处理
| 场景 | 处理 |
|---|---|
| 未登录访问 API | 401，前端跳登录 |
| 更新任务冲突 | 409 + 明确提示"已有任务运行" |
| 配置/文件校验失败 | 400，返回具体字段错误，前端展示 |
| 后台任务异常 | 记录 operation/run 错误状态，状态快照反映异常，前端提示并恢复控件 |
| 轮询请求失败 | 短暂网络错误自动保留上次数据并按间隔重试，连续失败给出提示 |
| RTMP 组件缺失 | 返回错误码，前端展示引导而非报错堆栈 |

## 8. 安全设计
- 管理 API 与公开订阅接口隔离，管理端强制认证；
- 密码仅存服务端配置，前端不接触明文（仅登录提交）；
- 会话签名、HttpOnly、SameSite；
- 文件操作限定在已知路径，文件名白名单，杜绝路径穿越；
- 登录失败限流；
- 前端所有动态内容使用 React 默认转义，接口返回只做数据不拼 HTML。

## 9. 构建与集成
- 前端 `npm install`（Node 环境按全局规范，依赖落在 `web_admin/node_modules`）；`npm run build` 产物输出到 `web_admin/dist`；
- Docker 构建增加前端构建阶段（node 镜像），产物拷贝到镜像内由 nginx 托管；
- 裸 Python 模式由 Flask 在 `/admin` 托管 `web_admin/dist`；
- nginx 模板增加 `/admin`、`/api/admin` 段（无需 WebSocket 段）。

## 10. 技术债与边界
- 从桌面端 `SourceEditor` 抽取解析纯函数时保持行为一致，仅做位置迁移；
- gunicorn 单 worker 是单例任务的前提，不支持多 worker 水平扩展（与现有部署一致）；
- Web 端不提供桌面端安装包式自升级、本地系统文件选择器。
