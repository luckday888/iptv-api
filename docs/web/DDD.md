# IPTV-API Web 管理端 数据库设计说明书（DDD）

版本：v1.0
日期：2026-09-29
配套文档：[PRD.md](PRD.md)、[SAD.md](SAD.md)、[ASD.md](ASD.md)

## 1. 数据存储总体说明

Web 管理端**不引入独立数据库**，复用现有两类存储：

| 存储 | 位置 | 用途 |
|---|---|---|
| SQLite 主库 | `output/data/channel_results.db` | 更新运行、频道、接口结果、候选池、截图、操作历史等 |
| SQLite RTMP 库 | `output/data/rtmp.db` | RTMP 推流结果数据 |
| 配置文件 | `config/config.ini` | 全部配置项（`[Settings]`），**新增管理密码配置** |
| 源文件 | `config/*.txt` | 模板、本地源、订阅、EPG、白/黑名单、别名 |
| 运行状态文件 | `output/data/run_state.json` | 当前/最近一次更新任务状态快照 |
| 截图文件 | `output/screenshots/` | 视频截图图片 |

设计原则：Web 端只读取/写入上述既有结构，不新增表；登录会话不落库（签名令牌无状态）。

## 2. SQLite 主库（channel_results.db）

由 `utils.channel_repository.ensure_channel_repository` 维护，`PRAGMA user_version=2`。

### 2.1 表关系总览
```
runs 1───* channel_results（经 output_snapshots / candidate_history / candidate_measurements 关联 run）
channels 1───* channel_results
channels 1───* channel_selection
channels 1───* candidate_pool（独立持久候选池）
channel_results 1───1 stream_screenshots（按 result_key）
stream_samples（按时间采样的码流统计）
operation_history（频道操作历史）
```

### 2.2 runs（更新运行记录）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| run_id | TEXT | PK | 运行唯一标识（uuid hex） |
| started_at | REAL | NOT NULL | 开始时间戳 |
| finished_at | REAL | | 结束时间戳 |
| status | TEXT | NOT NULL | running / success / failed |
| config_hash | TEXT | | 运行时配置哈希 |
| error | TEXT | | 失败错误信息 |

### 2.3 channels（频道）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| channel_key | TEXT | PK | 频道稳定标识（分类+名哈希） |
| category | TEXT | NOT NULL | 分类 |
| name | TEXT | NOT NULL | 频道名 |
| total_results | INTEGER | NOT NULL DEFAULT 0 | 接口总数 |
| untested_results | INTEGER | NOT NULL DEFAULT 0 | 待测数 |
| selection_mode | TEXT | NOT NULL DEFAULT 'auto' | auto / manual |
| valid_results | INTEGER | NOT NULL DEFAULT 0 | 有效接口数 |
| selected_results | INTEGER | NOT NULL DEFAULT 0 | 已选输出数 |
| best_speed | REAL | | 最佳速度 |
| min_delay | REAL | | 最低延迟 |
| max_resolution | TEXT | | 最高分辨率 |
| health | TEXT | NOT NULL DEFAULT 'unknown' | healthy / warning / offline / unknown |
| logo | TEXT | | 台标 URL |
| updated_at | REAL | NOT NULL | 更新时间戳 |

索引：`idx_channels_category(category, name)`。

### 2.4 channel_results（频道接口结果）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| channel_key | TEXT | NOT NULL，FK→channels | 所属频道 |
| result_key | TEXT | NOT NULL | 接口稳定标识 |
| url | TEXT | NOT NULL | 接口地址 |
| host | TEXT | | 主机 IP |
| headers | TEXT | | 请求头（JSON） |
| origin | TEXT | | 来源：subscribe/local/whitelist/hls |
| ipv_type | TEXT | | IPv4 / IPv6 |
| location | TEXT | | 归属地 |
| isp | TEXT | | 运营商 |
| speed | REAL | | 速度 |
| delay | REAL | | 延迟 |
| resolution | TEXT | | 分辨率 |
| fps | REAL | | 帧率 |
| video_codec | TEXT | | 视频编码 |
| audio_codec | TEXT | | 音频编码 |
| supply | INTEGER | NOT NULL DEFAULT 0 | 是否供给 |
| valid | INTEGER | NOT NULL DEFAULT 0 | 是否有效 |
| test_status | TEXT | | 测试状态 |
| error_type | TEXT | | 错误类型 |
| selected_rank | INTEGER | | 输出排名 |
| tested_at | REAL | | 测试时间 |
| last_seen_at | REAL | NOT NULL | 最近发现时间 |
| extra_data | TEXT | | 附加数据（JSON：date/catchup/tvg_logo/extra_info） |

主键：`(channel_key, result_key)`。
索引：`idx_results_result_key(result_key)`、`idx_results_channel_rank(channel_key, selected_rank)`。

视图：
- `channel_candidates`：`SELECT * FROM channel_results`（候选别名）；
- `candidate_selection`：由 `channel_selection` 投影（state、manual_rank、pinned、updated_at）。

### 2.5 channel_selection（手动输出选择）
| 字段 | 类型 | 约束 |
|---|---|---|
| channel_key | TEXT | NOT NULL，FK→channels |
| result_key | TEXT | NOT NULL |
| selection_rank | INTEGER | NOT NULL |
| selection_state | TEXT | NOT NULL DEFAULT 'included' |
| pinned | INTEGER | NOT NULL DEFAULT 0 |
| updated_at | REAL | NOT NULL |

主键：`(channel_key, result_key)`。

### 2.6 output_snapshots（输出快照）
| 字段 | 类型 | 约束 |
|---|---|---|
| run_id | TEXT | NOT NULL，FK→runs |
| channel_key | TEXT | NOT NULL，FK→channels |
| result_key | TEXT | NOT NULL |
| output_rank | INTEGER | NOT NULL |
| exported_at | REAL | NOT NULL |

主键：`(run_id, channel_key, result_key)`；索引 `idx_output_snapshots_run`。

### 2.7 candidate_history（候选历史）
| 字段 | 类型 | 约束 |
|---|---|---|
| run_id | TEXT | NOT NULL，FK→runs |
| channel_key | TEXT | NOT NULL |
| result_key | TEXT | NOT NULL |
| url | TEXT | NOT NULL |
| origin | TEXT | |
| first_seen_at | REAL | NOT NULL |
| last_seen_at | REAL | NOT NULL |

主键：`(run_id, channel_key, result_key)`；索引 `idx_candidate_history_key`。

### 2.8 candidate_pool（稳定候选池）
| 字段 | 类型 | 约束 |
|---|---|---|
| channel_key | TEXT | NOT NULL |
| result_key | TEXT | NOT NULL |
| url | TEXT | NOT NULL |
| origin | TEXT | |
| first_seen_at | REAL | NOT NULL |
| last_seen_at | REAL | NOT NULL |
| last_run_id | TEXT | |
| seen_count | INTEGER | NOT NULL DEFAULT 1 |

主键：`(channel_key, result_key)`；索引 `idx_candidate_pool_channel`。

### 2.9 candidate_measurements（候选测量历史）
| 字段 | 类型 | 约束 |
|---|---|---|
| run_id | TEXT | NOT NULL，FK→runs |
| channel_key | TEXT | NOT NULL |
| result_key | TEXT | NOT NULL |
| speed / delay / resolution / fps | | 测量值 |
| video_codec / audio_codec | TEXT | 编码 |
| valid | INTEGER | NOT NULL DEFAULT 0 |
| test_status / error_type | TEXT | 状态 |
| tested_at | REAL | |
| measured_at | REAL | NOT NULL |

主键：`(run_id, channel_key, result_key)`；索引 `idx_candidate_measurements_key`。

### 2.10 stream_samples（码流采样）
| 字段 | 类型 | 约束 |
|---|---|---|
| sampled_at | REAL | NOT NULL |
| result_key | TEXT | NOT NULL |
| clients | INTEGER | NOT NULL DEFAULT 0 |
| bw_in / bw_out | REAL | NOT NULL DEFAULT 0 |
| bytes_in / bytes_out | INTEGER | NOT NULL DEFAULT 0 |
| active | INTEGER | NOT NULL DEFAULT 0 |

主键：`(sampled_at, result_key)`；索引 `idx_stream_samples_time`。保留近 7 天。

### 2.11 operation_history（操作历史）
| 字段 | 类型 | 约束 |
|---|---|---|
| operation_id | TEXT | PK |
| operation | TEXT | NOT NULL（retest/capture 等） |
| target_type | TEXT | NOT NULL（channel/result/category） |
| target_key | TEXT | |
| started_at | REAL | NOT NULL |
| finished_at | REAL | |
| status | TEXT | NOT NULL（running/success/failed） |
| message | TEXT | |

### 2.12 stream_screenshots（截图记录）
| 字段 | 类型 | 约束 |
|---|---|---|
| result_key | TEXT | PK |
| filename | TEXT | |
| status | TEXT | NOT NULL（captured/failed） |
| captured_at | REAL | |
| attempted_at | REAL | NOT NULL |
| width / height | INTEGER | |
| error | TEXT | |

## 3. SQLite RTMP 库（rtmp.db）
由 `utils.db.ensure_result_data_schema` 维护。

### result_data
| 字段 | 类型 |
|---|---|
| id | TEXT PK |
| url | TEXT |
| headers | TEXT |
| video_codec | TEXT |
| audio_codec | TEXT |
| resolution | TEXT |
| fps | REAL |

## 4. 配置文件（config/config.ini）

### 4.1 现有结构
单文件，主节 `[Settings]`，约 60 项，键值对。完整键清单见 [docs/config.md](../config.md) 及默认文件 `config/config.ini`。配置读取由 `utils.config` 负责，支持环境变量覆盖、类型识别（bool/数字/枚举）。

### 4.2 新增配置项（Web 管理端）
在 `[Settings]` 节新增：

| 键 | 默认值 | 类型 | 说明 |
|---|---|---|---|
| admin_password | 空 | string | Web 管理端登录密码；首次启动为空时自动生成随机值并写入文件、打印到启动日志 |
| admin_session_days | 7 | int | 会话有效天数 |
| admin_login_rate_limit | 5 | int | 每分钟每 IP 最大登录失败次数 |

默认值同步到 `config/config.ini`（默认模板）与 `utils.config` 的配置描述/校验映射。

说明：
- 密码以明文形式存于配置文件（与项目现有"单实例、配置文件即密钥边界"一致）；配置文件本身由挂载卷权限保护；
- 不在数据库另存密码，避免双写；
- 修改密码走 `PUT /api/admin/auth/password`，同步写入配置文件。

## 5. 运行状态文件（run_state.json）

JSON 文件，任务管理器读写，结构：
```json
{
  "status": "idle|running|paused|cancelling|never_run",
  "updated_at": 173...,
  "title": "当前步骤",
  "percent": 42
}
```
用于进程重启/页面刷新后恢复任务状态展示；写入采用临时文件 + 原子替换。

## 6. 源文件数据格式（config/*.txt）

Web 端解析/序列化需与现有规则一致：

| 文件 | 行结构要点 |
|---|---|
| demo.txt（模板） | 分组 `分类名,#genre#`；行 `频道名,接口URL`；支持注释 |
| local.txt | 同模板，本地手动维护 |
| subscribe.txt | 每行一个订阅地址（txt/m3u URL） |
| epg.txt | 每行一个 EPG 地址 |
| whitelist.txt | 频道/接口白名单，含匹配规则字段 |
| blacklist.txt | 每行一个屏蔽 URL/关键字 |
| alias.txt | 频道名别名映射 |

解析规则从桌面端 `SourceEditor` 抽取为纯函数复用，不在数据库重复存储。

## 7. 会话存储（无状态）
- 登录成功颁发 `itsdangerous` 签名令牌，载荷含过期时间，不写入数据库；
- 令牌通过 HttpOnly Cookie 保存，服务端凭密钥验签；
- 登靠客户端清除 Cookie（令牌自然过期）；如需"立即失效"，可在配置更新密码时轮换签名密钥（实现可选）。

## 8. 数据一致性与并发
- 完整更新任务在进程内单例互斥（409）；
- SQLite 写操作使用现有 `_LOCK`/`_write_lock` 串行化，`busy_timeout=30000`；
- journal 模式由 `set_safe_journal_mode` 保证（WAL 或降级 DELETE）；
- 源文件写入采用临时文件 + 原子替换；
- gunicorn 单 worker 是上述单例与并发假设的前提。

## 9. 数据初始化与升级
- 首次启动：建库建表（`user_version=2`）；若 `admin_password` 为空则生成并提示；
- 升级：沿用现有 schema 迁移逻辑（`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN` 补齐列）；
- 新增的 3 个配置项由 `utils.config` 默认值兜底，旧配置文件缺失时自动按默认处理，不强制写入。
