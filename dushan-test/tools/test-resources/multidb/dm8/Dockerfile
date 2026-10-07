# 达梦 DM8 测试镜像：在 Debian 上静默安装服务端，安装程序与安装配置通过构建期挂载读取，不进入镜像层。
# 构建：从达梦官网下载 x86 Linux（CentOS7）安装包，解压出 ISO 中的 DMInstall.bin，与本目录的
# auto_install.xml、dm-start.sh 放在同一构建目录（如仓库 Temp/dm8/build），在 WSL 中执行：
#   docker build -t local/dushan-dm8:20260710 -f dushan-test/tools/test-resources/multidb/dm8/Dockerfile Temp/dm8/build
FROM public.ecr.aws/docker/library/debian@sha256:6ebd97fa83deb272194a2cf015b3d26a4d538e9ad3a7a79d544c8af5b0a01443
RUN useradd -m -u 1000 -s /bin/bash dmdba && mkdir -p /opt/dmdbms && chown dmdba:dmdba /opt/dmdbms
USER dmdba
# 安装与删除服务端用不到的文档、JDK、图形工具在同一层完成，镜像只保留服务端。
RUN --mount=type=bind,source=DMInstall.bin,target=/mnt/DMInstall.bin \
    --mount=type=bind,source=auto_install.xml,target=/mnt/auto_install.xml \
    /mnt/DMInstall.bin -q /mnt/auto_install.xml \
    && rm -rf /opt/dmdbms/doc /opt/dmdbms/desktop /opt/dmdbms/samples /opt/dmdbms/jdk \
       /opt/dmdbms/drivers /opt/dmdbms/uninstall /opt/dmdbms/uninstall.sh
COPY --chmod=755 dm-start.sh /usr/local/bin/dm-start.sh
ENV DM_HOME=/opt/dmdbms LD_LIBRARY_PATH=/opt/dmdbms/bin
EXPOSE 5236
ENTRYPOINT ["/usr/local/bin/dm-start.sh"]
