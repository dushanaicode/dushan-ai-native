import json
import os
import sys
from pathlib import Path

import pymysql
from redis import Redis

assert len(sys.argv) == 2 and sys.argv[1] in {"set", "restore"}
work = Path(os.environ["DUSHAN_AUDIT_WORKDIR"]).resolve()
assert work.is_relative_to((Path.cwd() / "Temp").resolve())
resources = json.loads((work / "resources.json").read_text(encoding="utf-8"))
server = json.loads((work / "server.json").read_text(encoding="utf-8"))
connection = pymysql.connect(
    host="127.0.0.1",
    port=resources["mysql_port"],
    user="root",
    password="",
    database=server["database"],
    autocommit=True,
)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT @@datadir")
        assert Path(cursor.fetchone()[0]).resolve() == Path(resources["mysql_datadir"]).resolve()
        cursor.execute(
            "SELECT id,access_token_validity_seconds FROM system_oauth2_client WHERE client_id='default'"
        )
        identifier, old = cursor.fetchone()
        target = work / "session-ttl-fixture.json"
        if sys.argv[1] == "set":
            target.write_text(
                json.dumps({"database": server["database"], "id": str(identifier), "old": old}),
                encoding="utf-8",
            )
            seconds = 20
        else:
            original = json.loads(target.read_text(encoding="utf-8"))
            assert original["database"] == server["database"] and original["id"] == str(identifier)
            seconds = original["old"]
        cursor.execute(
            "UPDATE system_oauth2_client SET access_token_validity_seconds=%s WHERE id=%s",
            (seconds, identifier),
        )
    cache = Redis(host="127.0.0.1", port=resources["redis_port"], decode_responses=True)
    try:
        assert cache.config_get("dir")["dir"] == resources["redis_dir"]
        keys = list(cache.scan_iter(match="*system:oauth_client*"))
        if keys:
            cache.delete(*keys)
    finally:
        cache.close()
    print(json.dumps({"seconds": seconds, "invalidated_client_cache_keys": len(keys)}))
finally:
    connection.close()
