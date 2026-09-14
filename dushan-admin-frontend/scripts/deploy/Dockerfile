FROM node:24.16.0-slim AS builder

# --max-old-space-size
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV NODE_OPTIONS=--max-old-space-size=8192
ENV TZ=Asia/Shanghai
ENV CI=true

# 启用 corepack，按 package.json 的 packageManager 字段使用锁定的 pnpm 版本
RUN npm i -g corepack && corepack enable

WORKDIR /app

# copy package.json and pnpm-lock.yaml to workspace
COPY . /app

# 安装依赖（锁文件冻结，不新增或升级任何包）
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
# 只构建 web-ele 及其 workspace 依赖，不再构建 playground 与其余四个应用
RUN pnpm run build:ele

RUN echo "Builder Success 🎉"

FROM nginx:stable-alpine AS production

# 复制 web-ele 构建产物
COPY --from=builder /app/apps/web-ele/dist /usr/share/nginx/html

# 后端地址由容器启动时的 API_UPSTREAM 环境变量注入（官方 nginx 镜像的 templates + envsubst
# 机制），只替换这一个变量名，避免 nginx 自身的 $host、$http_upgrade 等运行时变量被提前替换。
# 入口脚本按文件名顺序执行，05 号检查早于模板渲染；未设置或为空时容器直接退出，不使用猜测地址。
ENV NGINX_ENVSUBST_FILTER=^API_UPSTREAM$
COPY --from=builder --chmod=755 /app/scripts/deploy/05-require-api-upstream.sh /docker-entrypoint.d/05-require-api-upstream.sh
COPY --from=builder /app/scripts/deploy/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
