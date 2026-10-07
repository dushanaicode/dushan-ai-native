#!/bin/bash
# 达梦测试实例：数据目录在内存盘，每次启动重新初始化；字符集 UTF-8，时区 UTC；重做日志取最小值 256M，避免预分配占用大量内存。
set -euo pipefail
"$DM_HOME/bin/dminit" PATH=/dmdata DB_NAME=DAMENG INSTANCE_NAME=DMSERVER PORT_NUM=5236 \
    PAGE_SIZE=32 EXTENT_SIZE=16 LOG_SIZE=256 CHARSET=1 CASE_SENSITIVE=Y TIME_ZONE=+00:00 \
    SYSDBA_PWD="$DM_PASSWORD" SYSAUDITOR_PWD="$DM_PASSWORD" > /dmdata/dminit.log
exec "$DM_HOME/bin/dmserver" /dmdata/DAMENG/dm.ini -noconsole
