import json
import os

# 实例清单放在测试根目录而不是 starter_database/conftest.py：用例目录之间没有包隔离，
# `from conftest import X` 会被任意同级 conftest.py 抢占，新增带 conftest 的目录会让整组用例收集失败。
# sqlite 始终可用；其余真实实例由运行脚本通过环境变量注入，没有就只跑 sqlite。
TARGETS = [
    {"name": "sqlite", "url": None},
    *json.loads(os.environ.get("DUSHAN_DATABASE_TEST_URLS", "[]")),
]
