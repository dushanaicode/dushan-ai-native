import asyncio
import json
import os

import pytest

from starter_websocket.conftest import ORIGIN, ROOT


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_actual_frontend_client_over_real_transport(socket_case, tmp_path):
    case = socket_case
    scenario = tmp_path / "frontend-case.json"
    scenario.write_text(
        json.dumps({"origin": ORIGIN, "port": case.port, "token": case.token}), encoding="utf-8"
    )
    config = tmp_path / "frontend-live.config.mjs"
    base = (ROOT / "dushan-test/frontend/vitest.config.mjs").as_uri()
    test = (ROOT / "dushan-test/frontend/websocket-live.test.ts").as_posix()
    config.write_text(
        f"""import base from {json.dumps(base)};
export default {{...base,cacheDir:{json.dumps(str(tmp_path / "vite-cache"))},test:{{...base.test,
include:[{json.dumps(test)}],outputFile:{{junit:{json.dumps(str(tmp_path / "frontend.xml"))}}},maxWorkers:1}}}};
""",
        encoding="utf-8",
    )
    env = dict(os.environ, DUSHAN_WS_FRONTEND_CASE_FILE=str(scenario))
    for name in ("TEMP", "TMP", "TMPDIR"):
        env[name] = str(tmp_path)
    log = tmp_path / "frontend.log"
    with log.open("w", encoding="utf-8") as output:
        process = await asyncio.create_subprocess_exec(
            "node",
            str(ROOT / "dushan-admin-frontend/node_modules/vitest/vitest.mjs"),
            "run",
            "--config",
            str(config),
            "--configLoader",
            "native",
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=output,
        )
        try:
            code = await asyncio.wait_for(process.wait(), 45)
        finally:
            if process.returncode is None:
                process.terminate()
                await process.wait()
    assert code == 0, log.read_text(encoding="utf-8")
    assert "1 passed" in log.read_text(encoding="utf-8")
    state = await case.wait_state(lambda state: state["runtime"]["connections"] == 0)
    assert state["received"] == ["real-client"]
