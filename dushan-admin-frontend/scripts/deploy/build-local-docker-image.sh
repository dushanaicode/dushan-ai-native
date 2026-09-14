#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOG_FILE=${SCRIPT_DIR}/build-local-docker-image.log
ERROR=""
IMAGE_NAME="dushan-admin-web"

function build_image() {
    # Dockerfile 自己在镜像内部执行 pnpm install --frozen-lockfile，宿主机不需要预先安装依赖。
    # 构建上下文与 Dockerfile 都按脚本所在目录定位，从任意工作目录执行都一致。
    docker build "${SCRIPT_DIR}/../.." -f "${SCRIPT_DIR}/Dockerfile" -t ${IMAGE_NAME} || ERROR="build_image failed"
}

function stop_and_remove_container() {
    # Stop and remove the existing container so a new one can reuse the same name
    docker stop ${IMAGE_NAME} >/dev/null 2>&1
    docker rm ${IMAGE_NAME} >/dev/null 2>&1
}

function remove_dangling_previous_image() {
    # docker build 已经把 ${IMAGE_NAME} 这个 tag 指向新镜像；只按构建前记录的旧镜像 ID 删除，
    # 不按 tag 删除，避免误删刚构建出的新镜像
    if [[ -n "${OLD_IMAGE_ID}" && "${OLD_IMAGE_ID}" != "${NEW_IMAGE_ID}" ]]; then
        docker rmi "${OLD_IMAGE_ID}" >/dev/null 2>&1
    fi
}

function log_message() {
    if [[ ${ERROR} != "" ]];
    then
        >&2 echo "build failed, Please check build-local-docker-image.log for more details"
        >&2 echo "ERROR: ${ERROR}"
        exit 1
    else
        echo "docker image with tag '${IMAGE_NAME}' built successfully. Use below sample command to run the container"
        echo ""
        echo "docker run -d -p 8010:8080 -e API_UPSTREAM=http://<backend-host>:<port> --name ${IMAGE_NAME} ${IMAGE_NAME}"
    fi
}

OLD_IMAGE_ID=$(docker images -q ${IMAGE_NAME} 2>/dev/null)

echo "Info: Building docker image" | tee ${LOG_FILE}
build_image 1>> ${LOG_FILE} 2>> ${LOG_FILE}

if [[ ${ERROR} == "" ]]; then
    echo "Info: Build succeeded, replacing previous container and image" | tee -a ${LOG_FILE}
    NEW_IMAGE_ID=$(docker images -q ${IMAGE_NAME} 2>/dev/null)
    stop_and_remove_container
    remove_dangling_previous_image
fi

log_message | tee -a ${LOG_FILE}
