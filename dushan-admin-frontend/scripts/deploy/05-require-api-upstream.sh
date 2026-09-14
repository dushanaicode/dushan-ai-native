#!/bin/sh
set -eu

# 在官方镜像渲染 nginx 模板之前执行；缺少后端地址时直接退出，避免带着无效反代配置启动。
if [ -z "${API_UPSTREAM:-}" ]; then
  echo "API_UPSTREAM 未设置：请以 -e API_UPSTREAM=http://<后端主机>:<端口> 启动容器" >&2
  exit 1
fi
