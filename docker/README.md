# Native Docker 部署

默认组合是 MySQL + Redis。数据库、MQ、存储和监控各有独立 Compose；`app/` 提供完整前后端组合。当前 Windows 开发库 33160、Redis 63860 和既有 Jaeger 不由这些新增组合接管。

需要 Docker Engine 和支持 `include` 的 Compose v2.20+；本机验证使用 Ubuntu-24.04 WSL 内的 Engine。镜像默认 Linux/amd64，国产厂商包固定为本轮已验证的 x86_64 版本。

## 初次准备

在 Native 根目录，使用已安装项目依赖的 Python 执行：

```powershell
$toolTemp = Join-Path (Get-Location).Path 'Temp/docker-tools'
New-Item -ItemType Directory -Path $toolTemp -Force | Out-Null
$env:TEMP = $toolTemp
$env:TMP = $toolTemp
$env:TMPDIR = $toolTemp
$env:PYTHONDONTWRITEBYTECODE = '1'
.\dushan-admin-backend\.venv\Scripts\python.exe -B docker/prepare.py
```

脚本默认生成 `Temp/docker-runtime/`：随机凭据、Redis/RabbitMQ 配置、后端 `application*.yaml` 和 MySQL 空库 SQL。管理员是 `admin`，密码只写入该目录的 `credentials.json`，不在控制台输出。其他种子用户默认关闭，启用前需重置密码。数据库文件存储的 URL 随公开入口生成。重复运行会拒绝覆盖，防止凭据变化导致现有数据库失联。

后端继续读取 `application*.yaml`，没有后端 `.env`。runtime 内的厂商 `*.env` 仅供对应数据库/存储镜像的入口使用，不会传给后端配置加载器。

以下命令在 Linux/WSL 的 Native 根目录执行。先将 CLI 临时状态放到项目内；临时验证还必须选择数据根、containerd 和 BuildKit 缓存都位于 cwd/Temp 的独立 Engine，单独设置 CLI 目录不能隔离容器数据：

```sh
mkdir -p "$PWD/Temp/docker-tools"
export TMPDIR="$PWD/Temp/docker-tools" TEMP="$PWD/Temp/docker-tools" TMP="$PWD/Temp/docker-tools"
export DOCKER_CONFIG="$PWD/Temp/docker-tools/docker-cli"
# 本机临时验证时，显式设置已准备好的私有 Engine socket：
# export DOCKER_HOST=unix:///absolute/project/Temp/private-engine/docker.sock
```

如 runtime 不在默认目录，设置 Linux 可见的绝对路径 `NATIVE_RUNTIME_DIR`；不能把 `E:\...` 传给 WSL Docker。所有启动命令都使用相同 runtime，且执行前先 `config --quiet`。

## 两种基础运行方式

**应用在宿主机运行：**

```sh
docker compose -f docker/compose.yaml config --quiet
docker compose -f docker/compose.yaml up -d --wait
```

后端的本地 application 配置使用 MySQL `127.0.0.1:13306`、Redis `127.0.0.1:16379`；数据库名 `dushan_native`、数据库用户 `dushan`，凭据见 runtime。生成的 `application/` 使用的是容器服务名 `mysql`、`redis`，供下方完整组合使用，不能原样替换现有本机配置。

**前后端全部容器化：**

```sh
docker compose -f docker/app/compose.yaml config --quiet
docker compose -f docker/app/compose.yaml up -d --build --wait
```

入口 `http://localhost:18080`。后端只在内部网络开放 48080；前端已配置 API、WebSocket 和扫码入口。部署使用 `native_docker_refresh` Cookie，避免覆盖现有开发站的 `system_refresh`；同一域名并行多个 Docker 部署时，各自设置不同的 `refresh_cookie_name`。单 worker 运行后端并持有 Job owner。默认 `staging`，可访问 `/docs`、`/redoc`；生产环境设 `NATIVE_APP_ENV=prod`，按后端约束关闭交互 API 文档。

两种组合二选一：项目名和数据卷不同，默认端口相同；切换组合不会自动搬运数据库。已有 MySQL 数据卷不会再次执行初始化 SQL。发布基线直接维护后端 `sql/mysql/system/` 与 `infra/` 的建表及种子 SQL；已有数据卷须按实际数据单独评估变更，不能直接重新导入初始化目录。

空库仅加载当前 System/Infra 的建表与种子数据。所有 SQL 成功后才写入初始化完成标记；半初始化数据卷即使进程重启，也不会通过健康检查。遇到此类失败先检查容器日志与初始化 SQL，不能把重启或手工补标记当作修复。

## 可选服务

将命令中的 `FILE` 替换为下表路径：`docker compose -f FILE up -d --build --wait`。独立组合有自己的默认网络；应用要通过内部服务名访问其他组合时，应在同一个 Compose 入口中使用 `include` 组合所选文件，或明确配置可达的外部地址。

| 服务                           | Compose 文件                 | 默认宿主端口                     | 连接说明                                                   |
| ------------------------------ | ---------------------------- | -------------------------------- | ---------------------------------------------------------- |
| MySQL 8.4.11                   | `compose.yaml`               | 13306                            | 完整 System/Infra 初始化                                   |
| Redis 8.10.1                   | `compose.yaml`               | 16379                            | AOF、密码、noeviction；同时承担 MQ/协调用途                |
| PostgreSQL 17 + pgvector 0.8.6 | `db/postgres/compose.yaml`   | 15432                            | 库/用户均为 native；自动创建 vector 扩展                   |
| TiDB 8.5.3                     | `db/tidb/compose.yaml`       | 14000、状态14080                 | root，库 native，vendor-password；单节点 unistore 功能实验 |
| OceanBase CE 4.3.5.4           | `db/oceanbase/compose.yaml`  | 12881                            | root@test，库 native，vendor-password；mini 单节点实验     |
| openGauss 6.0.5                | `db/opengauss/compose.yaml`  | 15433                            | native，vendor-password；需预先导入镜像                    |
| KingbaseES V009R001C010B0004   | `db/kingbase/compose.yaml`   | 15434                            | kingbase，vendor-password；PG 模式、需导入镜像             |
| DM8 20250506 rev270902         | `db/dameng/compose.yaml`     | 15236                            | SYSDBA，vendor-password；UTF-8、大小写敏感、需导入镜像     |
| RabbitMQ 4.3.5                 | `mq/rabbitmq/compose.yaml`   | 15673、管理15674                 | 用户 dushan、vhost /                                       |
| Kafka 4.0.2                    | `mq/kafka/compose.yaml`      | 19092                            | KRaft 单节点；同网络用 kafka:29092                         |
| MinIO 2025-09-07 源码构建      | `storage/minio/compose.yaml` | 19000、控制台19001               | nativeadmin，minio-password；本地联调                      |
| FTP                            | `storage/ftp/compose.yaml`   | 12121、被动12100–12110           | dushan，ftp-password，目录 /upload                         |
| SFTP                           | `storage/sftp/compose.yaml`  | 12222                            | dushan，sftp-password，目录 /upload；持久化主机密钥        |
| Mailpit 1.27.8                 | `mailpit/compose.yaml`       | SMTP11025、页面18025             | 本地收件箱，无外部邮件投递                                 |
| Jaeger 2.21.0                  | `monitor/compose.yaml`       | 16686、OTLP4317                  | 保留既有配置，见 [Jaeger 说明](monitor/README.md)          |
| Tempo 2.8.2 + Grafana 12.1.1   | `monitor/tempo/compose.yaml` | 13200、14317/14318、Grafana13000 | Grafana 用户 nativeadmin；已配置 Tempo 数据源，保留72h     |

厂商镜像下载遵守厂商提供的账号、授权和使用范围，从 [openGauss](https://opengauss.org/en/download/)、[KingbaseES](https://www.kingbase.com.cn/download.html)、[达梦](https://eco.dameng.com/download/) 获取对应版本后 `docker load -i /path/in/Temp/vendor.tar`。三个配方默认使用固定本地镜像 ID 且 `pull_policy: never`，不会自动下载陌生替代镜像。导入另一构建时，核对版本/模式后显式设置对应 `NATIVE_*_IMAGE` 为 `docker image inspect --format '{{.Id}}' IMAGE` 得到的 ID。

国产服务用来复现数据库底座契约；完整业务初始化目前只交付 MySQL。openGauss/达梦接入还需后端可选 `database-domestic` 驱动组，默认应用镜像只带 MySQL/PostgreSQL 主线依赖。Kingbase/DM 的容器健康检查只证明监听端口，业务验证仍须真实认证和 SQL。主从复制、HA、国产全业务迁移不在这些单机配方中。

openGauss 使用 `SYS_NICE` 单项能力、4 GiB 容器内存限制和 PG 模式的 native 库，不启用 privileged。OceanBase 首次启动预留至少 12 GiB 可用磁盘（镜像之外）和充足内存；显式限制租户日志盘为 2 GiB，并通过当前镜像的 `OB_TENANT_INIT_SQL_DIR` 初始化数据库。金仓默认数据库为 test；直接使用达梦 SDK 时显式选择 UTF-8 客户端编码（`local_code=dmPython.PG_UTF8`）。

RabbitMQ/Kafka 配方已经提供，但当前邮件、短信生产者/消费者声明 `STREAM`，业务仍使用 Redis。切换 backend 必须同步修改为相应 QUEUE/TOPIC 契约并验证重试、死信、确认；选择其他 MQ 也不能移除系统使用的 Redis。

Kafka 区分宿主 EXTERNAL listener 和容器 INTERNAL listener。更换宿主地址/端口时同时设置 `NATIVE_KAFKA_HOST`、`NATIVE_KAFKA_PORT`；此开发配方的宿主端口仍只绑定回环。FTP 的被动地址通过 `NATIVE_FTP_PASV_ADDRESS` 指定，必须是实际 FTP 客户端能到达的地址；宿主联调默认 127.0.0.1，容器客户端需要改成可达地址。

## 对象存储与监控

MinIO 官方社区仓库已归档；本配方从固定官方 release 源码构建并校验下载 SHA-256，避开当前拒绝匿名拉取的历史镜像仓库。默认不开任何公共桶。首次登录控制台创建私有桶，再创建限于该桶的应用账号；应用不要长期使用 root 凭据。[官方维护状态](https://github.com/minio/minio)

后台新增 S3 存储时填写桶、应用凭据、endpoint 并开启 path-style。预签名上传/下载地址必须能被浏览器访问：容器服务名只能供容器使用，浏览器不能访问 `minio:9000`。云对象存储直接配置外部 endpoint，无需运行本地 MinIO。新生产环境应另行选定持续维护的 S3 服务；此历史版本用于现有本地联调。

当前 Jaeger 的容器名、项目名、数据目录保持。首次新机器运行它时先执行 `docker compose -f docker/monitor/compose.yaml pull`，再 `up -d`。Tempo 是可选追踪后端：宿主应用 OTLP 指向 `127.0.0.1:14317`，同网络应用指向 `tempo:4317`；Grafana 数据源已经指向 Tempo。Grafana 关闭匿名访问，不包含尚未接入的 Prometheus/Loki 指标或日志。

## HTTPS 入口

先准备浏览器信任的证书 `fullchain.pem`、`privkey.pem`，根据实际站点重新为**新部署**生成配置：

```powershell
.\dushan-admin-backend\.venv\Scripts\python.exe -B docker/prepare.py --output Temp/docker-production --origin https://admin.example.com
```

在 Linux/WSL 中设置 `NATIVE_RUNTIME_DIR` 为生成目录的绝对路径，并设置 `NATIVE_PUBLIC_ORIGIN=https://admin.example.com`、`NATIVE_SERVER_NAME=admin.example.com`、`NATIVE_TLS_DIR=/absolute/certificate-directory`、`NATIVE_HTTPS_PORT=443`。对外开放入口时显式设置 `NATIVE_HTTPS_BIND`；默认仍为回环地址。然后：

```sh
docker compose -f docker/app/compose.yaml -f docker/app/compose.https.yaml config --quiet
docker compose -f docker/app/compose.yaml -f docker/app/compose.https.yaml up -d --build --wait
```

`--origin`、前端 `NATIVE_PUBLIC_ORIGIN`、浏览器访问地址必须一致，且包含非标准端口。生成 HTTPS 配置时启用 Secure 刷新 Cookie，Origin 白名单和手机扫码地址一致；不会安装或修改系统证书信任。API/WebSocket 从 HTTPS 入口直接代理后端，保留协议、Host、客户端地址，不经过第二层 HTTP 代理。部署时按实际反代网段配置后端可信代理；不能把任意客户端提供的转发头当成真实 IP。

## 数据与运维

- 数据使用各 Compose 项目的命名卷；配置/随机凭据在 runtime 中。生产数据卷的位置和备份由所选 Engine 管理，不把临时验证盘当生产存储。
- 查看：`docker compose -f FILE ps`。停止：`docker compose -f FILE stop`。恢复：`docker compose -f FILE up -d --wait`。重建容器但保留数据：`down` 后 `up`。日常命令不附加 `-v`，不执行全局 prune。
- 保留 runtime 配置与密钥的受控备份。已有数据卷时只换密码文件不会更新数据库内部密码；按数据库的正常改密流程同步调整。
- MySQL/PostgreSQL 使用对应 dump 工具做逻辑备份并在独立实例验证恢复；备份命令的输出写入明确备份目录，密码用 secret/配置文件，不拼到命令历史。开启应用内数据库备份还需为后端镜像提供实际匹配的客户端工具，默认关闭。
- Redis AOF、RabbitMQ/Kafka 持久化和数据库复制都不能代替备份。文件存储按桶/目录备份，恢复后验证文件与数据库元数据一致；SFTP 同时保留主机密钥卷。
- 原生健康检查负责启动依赖顺序，运行中 MQ/Job/Redis 故障恢复由应用自身处理。不要同时启动多个持有相同 Snowflake machine ID 的独立应用实例；生成配置默认是单实例 201。

配置检查使用 `config --quiet`。不要把完整 `docker compose config`、`docker inspect` 或 runtime 文件发到公开日志，因为厂商镜像需要的环境变量中含凭据。
