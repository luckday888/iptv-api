# IPTV-API Web 管理端 API 接口文档（ASD）

版本：v1.0
日期：2026-09-29
配套文档：[PRD.md](PRD.md)、[SAD.md](SAD.md)、[DDD.md](DDD.md)

## 1. 通用约定

### 1.1 基础信息
- 所有管理接口前缀：`/api/admin`；
- 请求/响应统一使用 JSON（文件上传/下载除外），编码 UTF-8；
- 管理端静态资源：`/admin`；
- 协议：HTTP（生产建议前置 HTTPS 反代）。

### 1.2 鉴权
- 除 `POST /api/admin/auth/login` 外，所有接口需登录；
- 会话通过 HttpOnly Cookie（名 `iptv_admin_session`）传递；
- 未登录或会话过期：`401`；登录失败超限：`429`。

### 1.3 统一响应结构
常规成功直接返回数据对象/数组。错误时：
```json
{ "error": "错误概要", "details": { "字段": "具体错误" } }
```

### 1.4 通用状态码
| 码 | 含义 |
|---|---|
| 200 | 成功 |
| 400 | 参数/校验失败 |
| 401 | 未登录/会话失效 |
| 403 | 禁止（如只读项写入） |
| 404 | 资源不存在 |
| 409 | 状态冲突（如已有更新任务运行） |
| 429 | 请求过频（登录失败限流） |
| 500 | 服务端错误 |

### 1.5 分页约定
列表接口如需分页，使用 query：`page`（从 1 起）、`page_size`；响应：
```json
{ "items": [], "total": 0, "page": 1, "page_size": 50 }
```

---

## 2. 认证（auth）

### POST /api/admin/auth/login
登录。
- Body：`{"password": "xxx"}`
- 200：`{"username": "admin", "expires_at": 173...}` 并 Set-Cookie；
- 401：`{"error": "密码错误"}`；429：失败过频。

### POST /api/admin/auth/logout
退出登录，清除会话。200：`{"ok": true}`。

### GET /api/admin/auth/session
获取当前会话。200：`{"logged_in": true, "expires_at": ...}`；未登录 200 返回 `{"logged_in": false}`（不返回 401，供前端初始化判断）。

### PUT /api/admin/auth/password
修改管理密码。
- Body：`{"old_password": "xxx", "new_password": "xxx"}`
- 200：`{"ok": true}`；400：新密码不合规；401：旧密码错误。

---

## 3. 仪表盘（dashboard）

### GET /api/admin/dashboard/metrics
返回顶部指标。
```json
{
  "run_status": "idle|running|paused|cancelling",
  "channel_total": 74,
  "valid_total": 120,
  "service_status": "running|external|failed|unknown",
  "service_url": "http://host:8080",
  "next_run_at": 173...
}
```

### GET /api/admin/dashboard/channels
仪表盘频道结果表（支持搜索/分页）。
- Query：`search`、`page`、`page_size`
- 响应：分页对象，item 字段：
```json
{
  "channel_key": "...", "name": "CCTV-1", "category": "央视",
  "health": "healthy|warning|offline|unknown",
  "total_results": 5, "valid_results": 3,
  "best_speed": 3.2, "updated_at": 173..., "logo": "/logo/xx.png"
}
```

---

## 4. 更新任务（update）

### POST /api/admin/update/run
立即执行一次完整更新。
- 200：`{"ok": true}`；
- 409：`{"error": "已有更新任务在运行"}`。

### POST /api/admin/update/pause
暂停当前更新。200：`{"ok": true}`；409：任务未在运行。

### POST /api/admin/update/resume
继续被暂停的更新。200：`{"ok": true}`。

### POST /api/admin/update/cancel
取消当前更新。200：`{"ok": true}`。

### GET /api/admin/update/progress
返回当前任务状态快照（运行中约 1s 轮询）。
```json
{
  "status": "running|paused|cancelling|idle",
  "title": "正在获取订阅源",
  "percent": 42,
  "started_at": 173...,
  "finished": false,
  "last_event": {"level": "INFO", "message": "..."}
}
```
空闲时 `status=idle`、`percent=100`。

---

## 5. 频道中心（channels）

### 5.1 分类
#### GET /api/admin/channels/categories
分类侧栏数据。
```json
[
  {"category": "央视", "channel_count": 20,
   "healthy_count": 18, "warning_count": 2, "offline_count": 0,
   "valid_results": 60}
]
```

### 5.2 频道
#### GET /api/admin/channels
频道列表。
- Query：`category`、`health`、`search`、`page`、`page_size`
- 响应：分页对象，item：
```json
{
  "channel_key": "...", "category": "央视", "name": "CCTV-1",
  "total_results": 5, "untested_results": 1,
  "valid_results": 3, "selected_results": 3,
  "best_speed": 3.2, "min_delay": 80, "max_resolution": "1920x1080",
  "health": "healthy", "updated_at": 173..., "logo": "/logo/xx.png"
}
```

#### POST /api/admin/channels
新增频道。
- Body：`{"category": "自定义", "name": "我的频道"}`
- 200：`{"channel_key": "..."}`。

#### DELETE /api/admin/channels
批量删除频道。
- Body：`{"channel_keys": ["k1", "k2"]}`
- 200：`{"deleted": 2}`。

#### GET /api/admin/channels/{channel_key}
单个频道详情。404：不存在。

### 5.3 频道结果（接口）
#### GET /api/admin/channels/{channel_key}/results
该频道全部接口结果。
- Query：`filter`（all|valid|invalid|untested）、`search`
- 200：数组，item：
```json
{
  "result_key": "...", "url": "http://...", "host": "1.2.3.4",
  "origin": "subscribe|local|whitelist|hls", "ipv_type": "IPv4",
  "location": "北京", "isp": "电信",
  "speed": 3.2, "delay": 80, "resolution": "1920x1080",
  "fps": 25, "video_codec": "h264", "audio_codec": "aac",
  "valid": 1, "test_status": "valid", "error_type": null,
  "selected_rank": 1, "tested_at": 173...,
  "extra_data": {"tvg_logo": "...", "catchup": "...", "date": "..."},
  "screenshot": {"status": "captured", "filename": "...",
                 "width": 1920, "height": 1080}
}
```

#### POST /api/admin/channels/{channel_key}/results
手动新增接口。
- Body：`{"url": "http://..."}`
- 200：`{"result_key": "..."}`。

#### DELETE /api/admin/channels/{channel_key}/results
删除接口。
- Body：`{"result_keys": ["r1", "r2"]}`
- 200：`{"deleted": ["r1","r2"]}`。

### 5.4 重测
#### POST /api/admin/channels/{channel_key}/retest
对整个频道重测。
- 200：`{"operation_id": "..."}`（异步任务，经任务接口/进度查询）。

#### POST /api/admin/channels/{channel_key}/results/retest
对指定接口重测。
- Body：`{"result_keys": ["r1"]}`
- 200：`{"operation_id": "..."}`。

### 5.5 截图
#### POST /api/admin/channels/{channel_key}/results/screenshot
对指定接口截图。
- Body：`{"result_keys": ["r1"]}`
- 200：`{"operation_id": "..."}`。

#### GET /api/admin/screenshots/{result_key}
查看某接口截图元数据（状态、分辨率、文件名）。图片内容通过现有/新增的静态地址访问。

### 5.6 输出选择
#### GET /api/admin/channels/{channel_key}/selection
获取当前输出选择（rank 顺序）。
```json
{"mode": "auto|manual", "items": [{"result_key": "...", "rank": 1}]}
```

#### PUT /api/admin/channels/{channel_key}/selection
设置手动输出选择。
- Body：`{"result_keys": ["r2", "r1"]}`（按顺序）
- 200：`{"ok": true}`。

#### POST /api/admin/channels/{channel_key}/selection/reset
重置为自动选择。200：`{"ok": true}`。

### 5.7 台标
#### PUT /api/admin/channels/{channel_key}/logo
设置台标。
- Body：`{"logo": "url 或 上传后路径"}`；上传可走 `multipart/form-data`。
- 200：`{"ok": true}`。

### 5.8 名单
#### POST /api/admin/channels/{channel_key}/results/{result_key}/whitelist
加入白名单。
- Body：`{"url": "...", "name": "..."}`
- 200：`{"ok": true}`。

#### POST /api/admin/channels/{channel_key}/results/{result_key}/blacklist
加入黑名单。
- Body：`{"url": "..."}`
- 200：`{"ok": true}`。

### 5.9 导入导出
#### POST /api/admin/channels/import
上传本地源文件（txt/m3u）解析导入。
- 请求：`multipart/form-data`，字段 `file`；
- 200：`{"imported_channels": 10, "imported_results": 40}`。

#### GET /api/admin/channels/export
导出频道/结果数据为文件下载（格式由 `format` 指定，默认 txt）。

---

## 6. 订阅源（sources）

源类型 kind 取值：`template | local | subscribe | epg | whitelist | blacklist | alias`。

### GET /api/admin/sources/{kind}
读取源文件。
- Query：`mode`（raw|parsed，默认同时返回）
- 200：
```json
{
  "path": "config/whitelist.txt",
  "raw": "文件原始文本",
  "rows": [
    {"checked": true, "fields": ["CCTV-1","http://..."],
     "comment": null, "group": "分组名",
     "extra": {"rule": "name_or_url"}}
  ]
}
```

### PUT /api/admin/sources/{kind}
保存源文件。
- Body：`{"raw": "完整文本"}` 或 `{"rows": [...]}`（二选一，rows 由后端序列化）
- 200：`{"ok": true, "path": "..."}`；
- 400：校验/序列化失败，返回错误定位。

### POST /api/admin/sources/{kind}/import
上传文件替换/合并。
- 请求：`multipart/form-data`，字段 `file`，`merge`（true|false）
- 200：`{"ok": true}`。

### GET /api/admin/sources/{kind}/export
下载当前源文件。

### 模板分类（仅 kind=template）
#### GET /api/admin/sources/template/categories
模板分类侧栏：
```json
[{"category": "分类名", "count": 12, "group": "..."}]
```
#### POST/PUT/DELETE /api/admin/sources/template/categories
新增 / 重命名移动 / 删除模板分类（Body 含 `name`、`new_name`、`target_group` 等）。

#### POST /api/admin/sources/template/move
将选中条目移动到指定分类。
- Body：`{"rows": [...], "target_category": "..."}`。

---

## 7. 播放转推（rtmp）

### GET /api/admin/rtmp/runtime
RTMP 运行时快照（约 2s 轮询）。
```json
{
  "available": true,
  "status": "running|unavailable",
  "error_code": null,
  "error": "",
  "max_streams": 10,
  "active_count": 3,
  "starting_count": 1,
  "available_slots": 6,
  "sampled_at": 173...,
  "bw_out": 5000.0,
  "streams": [
    {"result_key": "...", "channel_key": "...", "channel_name": "CCTV-1",
     "clients": 1, "resolution": "1920x1080", "bw_out": 1500.0,
     "uptime": 120, "idle_remaining": 280}
  ]
}
```

### GET /api/admin/rtmp/channels
可转推频道列表（去重），供选择弹窗。
- Query：`search`
- 200：`[{"channel_key": "...", "channel_name": "...", "category": "...",
          "result_key": "...", "active": false, "starting": false}]`

### POST /api/admin/rtmp/streams/control
批量发起/停止转推（内部复用现有控制能力）。
- Body：`{"action": "start|stop|restart", "channel_keys": ["c1","c2"]}`
- 200：`{"success": 2, "total": 2, "errors": []}`；容量不足时 `errors` 给出提示。

> 说明：现有接口 `POST /api/rtmp/streams/<id>/<action>` 保持不变供本机服务用；Web 端用上述批量接口，后端做鉴权封装。

### GET /api/admin/rtmp/stream-url/{channel_key}
获取某频道转推/播放地址。200：`{"url": "rtmp://..."}`。

---

## 8. 日志（logs）

日志 kind 取值：`runtime | result | speed | statistics | unmatch`。

### GET /api/admin/logs/{kind}
读取日志（支持增量）。
- Query：`offset`（字节/行偏移）、`search`、`limit`
- 200：
```json
{"path": "...", "offset": 12345, "truncated": false,
 "lines": ["...", "..."]}
```

### DELETE /api/admin/logs/{kind}
清空该日志文件。200：`{"ok": true}`。

### GET /api/admin/logs/export
打包导出全部日志为 zip 下载。

---

## 9. 任务历史（tasks）

### GET /api/admin/tasks
合并返回更新运行记录与频道操作记录（倒序）。
- Query：`page`、`page_size`
- 200：分页对象，item：
```json
{
  "id": "run_id 或 operation_id",
  "source": "run|operation",
  "started_at": 173..., "finished_at": 173...,
  "status": "success|running|failed",
  "task": "full_update|retest_channel|capture_result_screenshot|...",
  "target": "频道 · CCTV-1",
  "duration": 12.5,
  "details": "错误或消息"
}
```

### GET /api/admin/diagnostics
导出系统诊断包为 zip 下载。

---

## 10. 设置（settings）

### GET /api/admin/settings
返回全部配置项及元数据。
```json
{
  "items": [
    {"key": "open_update", "value": "True", "kind": "bool",
     "description": "是否开启自动更新", "options": [],
     "advanced": false, "read_only": false,
     "env_name": null}
  ]
}
```

### PUT /api/admin/settings
批量保存配置。
- Body：`{"items": [{"key": "open_update", "value": "False"}, ...]}`
- 200：`{"ok": true}`；
- 400：校验失败，`details` 给出每项错误；
- 403：含只读/环境变量覆盖项被修改。

---

## 11. 关于（about）

### GET /api/admin/about/version
版本信息：
```json
{"name": "IPTV-API", "version": "3.0.0", "author": "Guovin",
 "build_time": "...", "repository": "https://github.com/Guovin/iptv-api"}
```

### GET /api/admin/about/update-check
检查新版本（后端请求 GitHub Releases，失败返回兜底）。
```json
{"has_update": false, "latest": "3.0.0", "current": "3.0.0",
 "release_url": "...", "checked_at": 173...}
```

### GET /api/admin/about/changelog
返回更新日志（CHANGELOG）内容（文本或按版本分段）。

---

## 12. 接口与现有模块映射（实现依据）
| 接口域 | 复用的现有模块/方法 |
|---|---|
| 更新 | `main.UpdateSource.run_once/pause/resume`、`utils.run_state` |
| 频道/结果 | `utils.channel_repository.*` |
| 重测/截图 | `utils.channel_operations.ChannelOperations` |
| 设置 | `utils.config`（get/set/save/validate） |
| 源文件 | `utils.user_actions`、各文件读写、抽取的解析纯函数 |
| RTMP | `utils.rtmp_stats.fetch_rtmp_snapshot`、`service.rtmp` |
| 诊断 | `utils.diagnostics.export_diagnostics` |
