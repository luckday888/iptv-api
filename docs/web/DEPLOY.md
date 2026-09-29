# IPTV-API Web 管理端部署手册

版本：v1.0
日期：2026-09-29
适用版本：含 Web 管理端的版本（代码合并至 master 后生效）

---

## 1. 架构说明

### 1.1 镜像形态：单镜像、多阶段构建

本项目**只有一个镜像**，由 `Dockerfile.web-admin` 分三个构建阶段（上游原版 `Dockerfile` 保持不变）：

| 阶段 | 基础镜像 | 产物 |
|---|---|---|
| `web_builder` | node:22-alpine | 管理端前端静态文件（`web_admin/dist`） |
| `builder` | python:3.14-alpine | Python venv、编译安装带 rtmp 模块的 nginx |
| runtime（最终镜像） | python:3.14-alpine | venv + nginx + 前端 dist + 业务代码 |

一个容器内运行三个进程（见 [entrypoint.sh](../../entrypoint.sh)）：

- **nginx**（监听 8080/1935）：托管管理端静态文件、反向代理管理 API、提供订阅接口入口、RTMP 转推、HLS、/stat 统计；
- **gunicorn**（监听 127.0.0.1:5180，sync 单 worker）：Flask 应用，提供订阅接口与 `/api/admin/*` 管理 API；
- **main.py**：按配置执行订阅源更新任务。

> 前端构建阶段与后端构建阶段互相独立，但**运行期在同一容器内**。如果部署规范要求前后端容器分离，参见 [第 7 章 手动双容器部署](#7-手动双容器部署不改代码)，无需修改仓库代码。

### 1.2 端口

| 端口 | 用途 |
|---|---|
| 8080（容器内） | HTTP：订阅接口 + 管理端 `/admin` + RTMP 统计 `/stat` |
| 1935（容器内） | RTMP 推流 |
| 5180（容器内回环） | gunicorn，不对外暴露 |

### 1.3 数据目录

所有持久化数据位于容器内两个目录，挂载这两个目录即可完成数据持久化：

| 容器路径 | 内容 |
|---|---|
| `/iptv-api/config` | 配置文件、订阅源、名单、EPG、台标、本地源、`user_config.ini`、`hls/` 视频源 |
| `/iptv-api/output` | 更新结果（m3u/txt）、EPG 产物、截图、SQLite 数据库（`data/channel_results.db`、`data/rtmp.db`） |

---

## 2. 快速开始

### 2.1 docker run（最小化）

```bash
docker run -d \
  --name iptv-api \
  --restart unless-stopped \
  -p 80:8080 \
  -e ADMIN_PASSWORD='你的强密码' \
  -v /opt/iptv-api/config:/iptv-api/config \
  -v /opt/iptv-api/output:/iptv-api/output \
  iptv-api:web-admin
```

访问：

- 订阅接口：`http://<宿主机IP>/`
- 管理端：`http://<宿主机IP>/admin`

### 2.2 docker compose（推荐）

使用仓库中的 `docker-compose.web-admin.yml`（可下载或复制内容，内部参数可按需更改）。首次使用先构建镜像：

```bash
docker build -f Dockerfile.web-admin -t iptv-api:web-admin .
```

启动 / 停止 / 查看日志：

```bash
# 可通过环境变量指定管理密码；留空则首启自动生成随机密码（查看启动日志获取）
ADMIN_PASSWORD='你的强密码' \
  docker compose -f docker-compose.web-admin.yml up -d
docker compose -f docker-compose.web-admin.yml down
docker compose -f docker-compose.web-admin.yml logs -f
```

> 上游原版 `docker-compose.yml` 部署的是不含 Web 管理端的官方镜像，两者互不影响。

---

## 3. 纯后端模式（不启用 Web 管理端）

直接使用**上游官方镜像**即可，无需使用 web-admin 镜像或覆盖启动命令。官方镜像包含订阅源更新、订阅接口、RTMP 转推、HLS、/stat 统计，仅缺少 Web 管理端：

| 路径 | 行为 |
|---|---|
| `/` 等订阅接口 | 正常提供 |
| `/hls`、`/stat` | RTMP 转推与统计正常可用 |
| `/admin`、`/api/admin/*` | **404**，镜像中无相关代码与页面 |

### 3.1 docker run

```bash
docker pull guovern/iptv-api:latest

# 官方镜像拉取失败时可用代理加速地址（可能版本较旧）
# docker pull docker.1ms.run/guovern/iptv-api:latest

docker run -d \
  --name iptv-api \
  --restart unless-stopped \
  -p 80:8080 \
  guovern/iptv-api:latest
```

### 3.2 docker compose

直接使用上游原版 `docker-compose.yml`：

```bash
docker compose up -d
# 修改宿主机端口
PORT=8088 docker compose up -d
```

### 3.3 用上游原版 Dockerfile 自行构建

需要离线构建或基于上游代码定制时，使用仓库中已恢复原样的 `Dockerfile`：

```bash
docker build -f Dockerfile -t iptv-api:latest .
```

### 3.4 源码方式

源码部署时不安装 Node、不执行前端构建，只运行后端两个进程：

```bash
pipenv run dev       # 终端1：订阅源更新
pipenv run service   # 终端2：订阅接口（默认 5180）
```

> 需求是"保留 RTMP 但关闭管理端"的场景同样由上游官方镜像天然满足，无需任何开关。

---

## 4. 自行构建镜像

需要在安装了 Docker 的主机上执行（本项目规范要求 Docker 构建在远程构建主机完成）：

```bash
# 克隆仓库
git clone <仓库地址> iptv-api
cd iptv-api

# 使用管理端专用 Dockerfile 构建（已内置 npmmirror / aliyun / tuna 镜像源）
docker build -f Dockerfile.web-admin -t iptv-api:web-admin .
```

构建参数（一般无需修改）：`APP_WORKDIR`（默认 `/iptv-api`）、`NGINX_VER`（1.27.4）、`RTMP_VER`（1.2.2）。

---

## 5. 环境变量说明

### 5.1 运行参数

| 变量 | 说明 | 默认值 |
|---|---|---|
| `ADMIN_PASSWORD` | 管理端登录密码；首次设置后持久化到 `config/user_config.ini` | 空（触发首启随机密码，见 5.3） |
| `IPTV_ADMIN_SECRET` | 会话签名固定密钥；不设置时由管理密码派生（改密后旧会话自动失效） | 空 |
| `ADMIN_SESSION_DAYS` | 会话有效期天数（1~90） | 7 |
| `ADMIN_LOGIN_RATE_LIMIT` | 60 秒内同一 IP 最大登录失败次数（1~100） | 5 |
| `APP_PORT` | 容器内 gunicorn 端口 | 5180 |
| `NGINX_HTTP_PORT` | 容器内 HTTP 端口，一般保持默认 | 8080 |
| `NGINX_RTMP_PORT` | 容器内 RTMP 端口 | 1935 |
| `PUBLIC_URL` | 订阅接口完整对外地址，如 `https://iptv.example.com`（推荐设置） | 空（用配置文件值） |
| `PUBLIC_SCHEME` | 对外协议 `http`/`https` | http |
| `PUBLIC_DOMAIN` | `PUBLIC_URL` 为空时使用的域名或 IP | 127.0.0.1 |
| `PUBLIC_PORT` | `PUBLIC_URL` 为空时使用的对外端口 | 80 |
| `HTTP_PROXY` | 订阅源/EPG 抓取代理（不用于测速） | 空 |
| `CDN_URL` | CDN 加速地址 | 空 |

### 5.2 通用配置覆盖机制

`config/config.ini` 中的**任意配置项**都可以通过环境变量覆盖，查找顺序：

```
<键名>  →  <键名大写>  →  <段名_键名>  →  <段名_键名大写>
```

例：`[Settings]` 段的 `open_update` 可用 `OPEN_UPDATE=false` 覆盖。
被环境变量覆盖的配置项在管理端「设置」页标记为只读，避免界面值与环境值冲突。

### 5.3 管理密码初始化策略

- 若设置了 `ADMIN_PASSWORD`：使用该密码；
- 若未设置且 `config/user_config.ini` 中无密码：**首次启动自动生成随机密码**，写入用户配置文件，并在启动日志中明文打印一次（`[初始化]` 开头）；
- 登录后可在「设置 → 修改密码」中改密（需验证旧密码，改密后所有会话失效需重新登录）；
- 密码尚未初始化期间，登录接口返回 403。

查看随机密码：

```bash
docker logs iptv-api 2>&1 | grep 初始化
```

---

## 6. 数据持久化与配置

### 6.1 挂载要点

- 首次启动时，镜像内默认配置会自动补齐到挂载的空 `config/` 目录（已存在的文件不覆盖）；
- 修改订阅源、名单、配置既可在管理端操作，也可直接编辑宿主机挂载目录中的文件；
- 数据库（频道结果、RTMP 状态）位于 `output/data/`，删除该目录会丢失频道测试结果与操作历史。

### 6.2 常用文件位置

| 文件 | 路径（容器内） |
|---|---|
| 主配置 | `config/config.ini` |
| 用户配置（含管理密码） | `config/user_config.ini` |
| 订阅源 | `config/subscribe.txt` |
| 白/黑名单 | `config/whitelist.txt`、`config/blacklist.txt` |
| 别名 / EPG | `config/alias.txt`、`config/epg.txt` |
| 更新结果 | `output/ipv4/result.txt`、`output/ipv6/result.txt` |
| 接口截图 | `output/screenshots/` |

---

## 7. 手动双容器部署（不改代码）

适用于部署规范要求"网关/前端"与"后端"容器分离的场景。两个容器使用**同一镜像**，通过覆盖启动命令实现分工：网关容器只跑 nginx，后端容器只跑 main.py + gunicorn。

### 7.1 拓扑

```
宿主机 :80/:1935 ──→ iptv-gateway (nginx: 静态文件 + 反代 + RTMP)
                          │ 容器网络 iptv-net
                          ▼
                     iptv-backend (gunicorn:5180 + main.py)
                          │
                     config/ output/ （共享挂载）
```

### 7.2 docker-compose 示例

创建 `docker-compose.split.yml`：

```yaml
services:
  backend:
    image: iptv-api:web-admin
    container_name: iptv-backend
    restart: unless-stopped
    networks: [iptv-net]
    volumes:
      - ./config:/iptv-api/config
      - ./output:/iptv-api/output
    environment:
      ADMIN_PASSWORD: "请修改为强密码"
      PUBLIC_URL: "http://192.168.1.10"
    # 不启动 nginx，只跑更新任务与 gunicorn；绑 0.0.0.0 供网关访问
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        set -e
        for file in /iptv-api-config/*; do
          name=$$(basename "$$file")
          [ -e "$$APP_WORKDIR/config/$$name" ] || cp -r "$$file" "$$APP_WORKDIR/config/$$name"
        done
        . $$APP_WORKDIR/.venv/bin/activate
        export IPTV_API_PLAIN_OUTPUT=1
        python -u $$APP_WORKDIR/main.py &
        exec env IPTV_API_SKIP_VERSION_CHECK=1 python -u -m gunicorn \
          service.app:app -b 0.0.0.0:$$APP_PORT --workers=1 --timeout=1000

  gateway:
    image: iptv-api:web-admin
    container_name: iptv-gateway
    restart: unless-stopped
    networks: [iptv-net]
    depends_on: [backend]
    ports:
      - "80:8080"
      - "1935:1935"
    environment:
      APP_PORT: "5180"
      NGINX_HTTP_PORT: "8080"
      NGINX_RTMP_PORT: "1935"
    # 生成 nginx 配置后，将回环上游替换为 backend 容器，再以前台方式运行
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        set -e
        sed -e "s/\$${APP_PORT}/$$APP_PORT/g" \
            -e "s/\$${NGINX_HTTP_PORT}/$$NGINX_HTTP_PORT/g" \
            -e "s/\$${NGINX_RTMP_PORT}/$$NGINX_RTMP_PORT/g" \
            -e "s|\$${IPV6_HTTP_LISTEN}||g" \
            /etc/nginx/nginx.conf.template > /tmp/nginx.conf
        sed -i "s|http://127.0.0.1:$$APP_PORT|http://backend:$$APP_PORT|g" /tmp/nginx.conf
        exec nginx -c /tmp/nginx.conf -g 'daemon off;'

networks:
  iptv-net:
    driver: bridge
```

启动：

```bash
docker compose -f docker-compose.split.yml up -d
```

> 注意事项：
> - YAML 中 `$$` 为 compose 对 shell 变量的转义，直接照抄即可；
> - 前端静态文件来自网关容器镜像内 `/usr/local/nginx/html/admin`，升级前端需更新网关容器镜像；
> - RTMP 的 `on_done` 回调同样经 sed 指向后端容器，无需额外配置。

---

## 8. HTTPS 部署

推荐架构：外部 HTTPS 网关（nginx / Caddy / 云负载均衡）→ 本容器（HTTP 8080）。

### 8.1 外部 nginx 反代示例

```nginx
server {
    listen 443 ssl;
    server_name iptv.example.com;

    ssl_certificate     /etc/letsencrypt/live/iptv.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iptv.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

要点：

- 必须透传 `X-Forwarded-Proto`：会话 cookie 在 https 下自动加 `Secure` 属性；
- 必须透传 `X-Real-IP`：登录限流按该 IP 分桶；
- 此时 `PUBLIC_URL=https://iptv.example.com`；
- 管理端路径仍为 `/admin`，无需改动。

### 8.2 Caddy 示例

```
iptv.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

Caddy 自动签发证书并默认透传上述头信息。

---

## 9. 源码部署（Linux / macOS）

适用于不便使用 Docker 的环境。生产环境仍建议使用 Docker 镜像。

### 9.1 系统依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | 3.14 | 后端运行（pipenv 管理虚拟环境） |
| Node.js | 22.x | 构建管理端前端 |
| FFmpeg | 任意较新版本 | 分辨率检测、截图 |
| nginx（带 rtmp 模块） | 较新 | 仅在需要 RTMP 转推时必须；纯订阅/管理可用普通反代 |

### 9.2 后端环境

```bash
git clone <仓库地址> iptv-api
cd iptv-api

# 安装依赖到项目内虚拟环境（.venv）
pip install pipenv
PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy
```

### 9.3 构建前端

```bash
cd web_admin
npm install
npm run build        # 产物输出到 web_admin/dist
cd ..
```

开发模式（热更新，可选）：

```bash
cd web_admin
npm run dev          # 监听 5181，自动代理 /api 到 127.0.0.1:5180
```

### 9.4 启动进程

需要两个常驻进程（与容器内一致）：

```bash
# 终端1：订阅源更新任务
pipenv run dev               # python main.py

# 终端2：Web 服务（开发/调试）
pipenv run service           # python service/app.py，监听 config.app_port（默认 5180）
```

生产方式用 gunicorn：

```bash
.venv/bin/python -m gunicorn service.app:app \
  -b 127.0.0.1:5180 --workers=1 --timeout=1000
```

### 9.5 systemd 托管（Linux 生产）

`/etc/systemd/system/iptv-update.service`：

```ini
[Unit]
Description=IPTV-API update worker
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/iptv-api
ExecStart=/opt/iptv-api/.venv/bin/python main.py
Restart=on-failure
Environment=IPTV_API_PLAIN_OUTPUT=1

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/iptv-web.service`：

```ini
[Unit]
Description=IPTV-API web service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/iptv-api
ExecStart=/opt/iptv-api/.venv/bin/python -m gunicorn service.app:app -b 127.0.0.1:5180 --workers=1 --timeout=1000
Restart=always

[Install]
WantedBy=multi-user.target
```

启用：

```bash
systemctl daemon-reload
systemctl enable --now iptv-update iptv-web
```

### 9.6 源码部署的前端托管

由系统 nginx 托管 `web_admin/dist` 并反代 API（参考配置，按需调整；RTMP/HLS 配置可参照仓库 [nginx.web-admin.conf.template](../../nginx.web-admin.conf.template)）：

```nginx
server {
    listen 80;
    server_name iptv.example.com;

    location /admin {
        alias /opt/iptv-api/web_admin/dist;
        try_files $uri $uri/ /admin/index.html;
    }

    location /api/admin/ {
        proxy_pass http://127.0.0.1:5180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:5180;
        proxy_set_header Host $host;
    }
}
```

> 注意：源码部署时 `register_web` 以进程工作目录（cwd）下的 `web_admin/dist` 定位静态文件，需保证工作目录为项目根目录。

### 9.7 Windows / macOS 桌面端

如需原 PySide6 桌面界面：

```bash
pipenv run ui          # 启动桌面端
pipenv run ui_build    # 打包桌面安装包
```

---

## 10. 升级

### 10.1 镜像升级

```bash
# 在构建主机重新构建镜像
docker build -f Dockerfile.web-admin -t iptv-api:web-admin .
docker compose -f docker-compose.web-admin.yml up -d   # 使用新镜像重建容器
```

`config/`、`output/` 在挂载卷中，升级不丢失；镜像内新增的默认配置项会自动补齐（已存在文件不覆盖）。

### 10.2 源码升级

```bash
git pull
PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy
cd web_admin && npm install && npm run build && cd ..
sudo systemctl restart iptv-update iptv-web
```

---

## 11. 验证与排障

### 11.1 部署验证

```bash
# 订阅接口（应返回播放列表内容）
curl -I http://127.0.0.1/

# 管理端页面（应返回 200 与 HTML）
curl -I http://127.0.0.1/admin/

# 未登录访问管理 API（应返回 401）
curl -i http://127.0.0.1/api/admin/auth/session
```

浏览器访问 `http://<宿主机IP>/admin`，应自动跳转登录页；使用部署时设置的密码（或首启随机密码）登录。

### 11.2 常见问题

| 现象 | 原因与处理 |
|---|---|
| 管理端白屏 | 镜像过旧或静态资源 MIME 异常；确认使用含内联 MIME 配置的新镜像；浏览器开发者工具 Network 查看 `/admin/assets/*.js` 是否 200 且类型为 `application/javascript` |
| 登录提示"失败次数过多" | 同 IP 60 秒内失败次数达到阈值；等待窗口过期，或调大 `ADMIN_LOGIN_RATE_LIMIT` |
| 登录提示"管理密码未初始化" | 密码为空且初始化未完成；查看容器日志中 `[初始化]` 随机密码，或设置 `ADMIN_PASSWORD` 后重建 |
| 不知道初始密码 | `docker logs iptv-api 2>&1 grep 初始化` |
| 设置保存返回 400 | 按响应 `details` 中每项提示修正；环境变量锁定项需改环境变量而非在页面修改 |
| 订阅地址不正确 | 设置 `PUBLIC_URL` 为完整对外地址后重新执行更新 |
| RTMP 转推不可用 | 确认 1935 端口已映射、容器镜像为带 rtmp 模块版本；查看 `/stat` 与容器错误日志 |
| 容器不停重启 | 查看 `docker logs iptv-api`；多为挂载目录权限或配置文件损坏，可临时移除挂载排查 |

### 11.3 日志位置

| 日志 | 位置 |
|---|---|
| 容器标准输出（nginx + 更新任务 + gunicorn） | `docker logs iptv-api` |
| 运行日志 | `output/logs/`（管理端「日志」页可查看与清空） |
| nginx 错误日志 | 容器内 `/var/log/nginx/error.log`（已链接到标准错误输出） |
