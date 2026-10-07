#!/bin/bash
set -e
cp -a /root/.obd /obhome/.obd
cp -a /root/.ssh /obhome/.ssh
cp /root/.bashrc /root/.bash_profile /obhome/
export HOME=/obhome
cd /root
/usr/sbin/sshd
exec /root/boot/start.sh
