#!/bin/sh
# 仅在全部初始化 SQL 成功后运行；失败的半初始化数据卷不能变成健康实例。
touch /var/lib/mysql/.native-initialized
