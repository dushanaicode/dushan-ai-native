# 生产部署说明

本目录只发布 `web-ele` 一个应用；镜像内的 nginx 只做静态资源托管与 `/api` 反向代理，不内置认证、租户或业务逻辑。

## 构建

```sh
docker build . -f scripts/deploy/Dockerfile -t dushan-admin-web
```

构建阶段（`builder`）在镜像内部执行 `pnpm install --frozen-lockfile` 与 `pnpm run build:ele`（即 Turbo 的 `--filter=@vben/web-ele`，会连带构建其依赖的 `packages/**`，不构建 `playground` 与其余四个 Vben 应用）；Node、pnpm 版本与仓库根 `.node-version`（`24.16.0`）、`package.json` 的 `packageManager`（`pnpm@11.16.0`）保持一致。运行阶段（`production`）基于 `nginx:stable-alpine`，只复制 `apps/web-ele/dist`、`default.conf.template` 与启动检查脚本 `05-require-api-upstream.sh`。

当前 web-ele 生产配置（`apps/web-ele/.env.production`）没有必须在构建期提供的业务参数（`clientId`、监控地址等），因此构建不新增必填的 `--build-arg`。

## 运行时变量

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `API_UPSTREAM` | 是 | 后端来源地址，只填协议 + 主机[:端口]，例如 `http://backend:48080`；不带路径、不带末尾斜杠。容器启动时由官方 nginx 镜像的 `docker-entrypoint` 通过 `envsubst` 注入模板。启动脚本 `05-require-api-upstream.sh` 先于模板渲染执行，变量未设置或为空时容器直接退出并提示，不会退回到某个猜测地址。 |

```sh
docker run -d -p 8010:8080 -e API_UPSTREAM=http://backend:48080 --name dushan-admin-web dushan-admin-web
```

容器内监听 `8080`；上面的示例把宿主机 `8010`映射到容器 `8080`，可按部署环境改成实际需要的宿主机端口。

## `/api` 路径语义

与开发代理（`apps/web-ele/vite.config.ts` 的 `server.proxy['/api']`）保持一致：浏览器请求同源 `/api/...`，nginx 剥离 `/api` 前缀后转发到 `API_UPSTREAM`（例如 `/api/health` -> `http://backend:48080/health`）；后端返回的错误原样透传，不会被 SPA 回退成 `index.html`。页面与接口同源，静态资源响应不添加 `Access-Control-Allow-Origin` 等跨域头。

## WebSocket、SSE 与上传

- `/api/` 反代已设置 `Upgrade`/`Connection` 头并按 `$http_upgrade` 做协议升级，支持 WebSocket。
- 同一 `/api/` 位置关闭了代理缓冲（`proxy_buffering off`）并把读写超时设置为 3600 秒，避免 SSE 长连接被提前截断或缓冲导致事件延迟下发。
- `client_max_body_size` 固定为 `20m`：当前 Native 后端尚无具体的文件上传契约，先给一个覆盖常见图片/文档上传的明确值；后续有实际更大体积的上传接口时，按需调整这一个数值即可。

## 静态资源缓存

规则对应 `pnpm build:ele` 生成的 `apps/web-ele/dist` 目录结构，构建输出结构变化时需同步调整：

- `index.html`、`_app-config-*.js`（运行时注入的应用配置脚本）：`Cache-Control: no-store`，保证发布新版本或新配置立即生效。
- `js/`、`css/`、`jse/` 三个目录下的文件名都带内容哈希：`Cache-Control: public, max-age=31536000, immutable`，可长期强缓存。

压缩使用 nginx 运行时 `gzip`，与 `.env.production` 的 `VITE_COMPRESS=none` 保持一致（构建期不产出 `.gz` 静态压缩文件，因此不使用 `gzip_static`）。

## 本地镜像脚本

`build-local-docker-image.sh`（仍为 Bash，需要 Docker 与类 Unix shell 环境；跨平台改写留待后续按需处理）：

1. 先执行 `docker build`；只有构建成功才会停止并删除旧容器、清理旧镜像——构建失败时线上仍在运行的旧容器不受影响。
2. 镜像名固定为 `dushan-admin-web`。
3. 不再预先在宿主机执行 `pnpm install`：依赖安装完全在 Dockerfile 的构建阶段内完成，宿主机不需要提前准备 Node/pnpm 环境。
4. 构建上下文与 Dockerfile 按脚本所在目录定位，可以从任意工作目录执行（包括 `pnpm build:docker`）。
5. 构建成功后会打印一条包含 `API_UPSTREAM` 示例的 `docker run` 命令；日志写入脚本同目录下的 `build-local-docker-image.log`。
