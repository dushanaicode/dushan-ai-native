"""数据库用例共用的真实实例清单，按项目约定放在测试根目录。

放在这里而不是 starter_database/conftest.py：用例目录之间没有包隔离，
`from conftest import X` 会被任意一个同级 conftest.py 抢占，只要新增一个
带 conftest 的测试目录，整组数据库用例就会在收集阶段导入失败。
"""

import json
import os

# sqlite 始终可用；其余真实实例由运行脚本通过环境变量注入，没有就只跑 sqlite。
TARGETS = [
    {"name": "sqlite", "url": None},
    *json.loads(os.environ.get("DUSHAN_DATABASE_TEST_URLS", "[]")),
]
