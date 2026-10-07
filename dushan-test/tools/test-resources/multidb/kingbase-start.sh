#!/bin/bash
set -e
cp -a /home/kingbase/install/kingbase /kb/kingbase
export PATH=/kb/kingbase/bin:$PATH
export LD_LIBRARY_PATH=/kb/kingbase/lib
mkdir -p /kb/data
chmod 700 /kb/data
/kb/kingbase/bin/initdb -U"$DB_USER" -x "$DB_PASSWORD" -D /kb/data -E UTF-8 -m "$DB_MODE"
/kb/kingbase/bin/sys_ctl -D /kb/data -l /kb/data/logfile start
exec tail -F /kb/data/logfile
