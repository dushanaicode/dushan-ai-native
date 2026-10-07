import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from uuid import uuid4

import aioftp
import pytest
from pydantic import SecretStr, ValidationError

from framework.starter_job.core.job_registry import JobRegistry
from framework.starter_job.exception.job_exception import JobException
from module_infra.config.infra_backup_settings import InfraBackupSettings
from module_infra.framework.file.core.client.ftp.ftp_file_client import FtpFileClient
from module_infra.framework.file.core.client.ftp.ftp_file_client_config import FtpFileClientConfig
from module_infra.job.data_source import database_backup_job as backup_module
from module_infra.job.data_source.database_backup_job import DatabaseBackupJob
from module_infra.job.data_source.database_backup_parameters import DatabaseBackupParameters


def test_backup_only_exposes_full():
    assert DatabaseBackupParameters().backup_type == "full"
    assert DatabaseBackupParameters(backup_type="full").backup_type == "full"
    with pytest.raises(ValidationError):
        DatabaseBackupParameters(backup_type="incremental")
    registry = JobRegistry([DatabaseBackupJob], "UTC")
    with pytest.raises(JobException) as caught:
        registry.parameters(
            SimpleNamespace(
                handler_key="infra.database.backup", parameters={"backup_type": "incremental"}
            )
        )
    assert isinstance(caught.value.__cause__, ValidationError)


def test_backup_parameters_reject_unknown_fields_and_invalid_assignment():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DatabaseBackupParameters(backup_type="full", output_directory="unexpected")
    parameters = DatabaseBackupParameters.model_validate({})
    assert parameters.model_dump() == {"backup_type": "full"}
    with pytest.raises(ValidationError, match="literal_error"):
        parameters.backup_type = "incremental"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        "output_file",
        "mkdir",
        "write",
        "partial_write",
        "spawn",
        "process",
        "timeout",
        "cancel",
        "success",
    ],
)
async def test_backup_credentials_cover_whole_lifetime(failure, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    identifier = uuid4().hex
    temporary = Path.cwd() / "Temp/infra-backup" / identifier
    credential = temporary / "client.cnf"
    output_directory = tmp_path / "outputs"
    if failure == "output_file":
        output_directory.write_text("existing file", encoding="utf-8")
    job = DatabaseBackupJob()
    job.settings = InfraBackupSettings(
        enabled=True,
        executable="mysqldump-fixture",
        output_directory=str(output_directory),
        data_source="primary",
        timeout_seconds=0.1 if failure == "timeout" else 10,
    )
    source = SimpleNamespace(
        name="primary",
        url=SecretStr("mysql+aiomysql://test:BackupOnlySecret123@127.0.0.1:12345/fixture"),
    )

    async def sources():
        return ()

    job.database_settings = SimpleNamespace(sources=(source,))
    job.runtime_sources = SimpleNamespace(load_sources=sources)
    monkeypatch.setattr(backup_module, "uuid4", lambda: SimpleNamespace(hex=identifier))
    original_write, original_mkdir = Path.write_text, Path.mkdir

    def write(path, data, *args, **kwargs):
        if path == credential and failure in {"write", "partial_write"}:
            if failure == "partial_write":
                original_write(path, "password=BackupOnlySecret123", encoding="utf-8")
            raise OSError("fixture credential write failure")
        return original_write(path, data, *args, **kwargs)

    def mkdir(path, *args, **kwargs):
        if path == output_directory and failure == "mkdir":
            raise PermissionError("fixture output mkdir failure")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write)
    monkeypatch.setattr(Path, "mkdir", mkdir)
    script = tmp_path / "dump_fixture.py"
    script.write_text(
        "import sys,time\nprint('CREATE TABLE fixture (id INT);', flush=True)\nif sys.argv[1] in ('cancel','timeout'): time.sleep(60)\nif sys.argv[1] == 'process': sys.exit(7)\n",
        encoding="utf-8",
    )
    original_spawn = asyncio.create_subprocess_exec
    spawned = []
    ready = asyncio.Event()

    async def spawn(*arguments, **kwargs):
        assert credential.exists()
        assert "BackupOnlySecret123" not in " ".join(arguments)
        assert not {"--flush-logs", "--source-data=2"}.intersection(arguments)
        assert kwargs["env"]["TEMP"] == str(temporary)
        if failure == "spawn":
            raise OSError("fixture process spawn failure")
        process = await original_spawn(sys.executable, "-B", str(script), failure, **kwargs)
        spawned.append(process)
        ready.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    try:
        if failure == "success":
            result = Path(await job.execute(DatabaseBackupParameters(), None))
            assert "CREATE TABLE fixture" in result.read_text(encoding="utf-8")
        elif failure == "cancel":
            task = asyncio.create_task(job.execute(DatabaseBackupParameters(), None))
            await asyncio.wait_for(ready.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            expected = TimeoutError if failure == "timeout" else OSError
            with pytest.raises(expected) as caught:
                await job.execute(DatabaseBackupParameters(), None)
            if failure in {"write", "partial_write", "spawn", "mkdir"}:
                assert "fixture" in str(caught.value)
        assert not credential.exists()
        assert all(process.returncode is not None for process in spawned)
        if failure in {"spawn", "process", "timeout", "cancel"}:
            assert len(list(output_directory.glob("*.failed.sql"))) == 1
        captured = capsys.readouterr()
        assert "BackupOnlySecret123" not in captured.out + captured.err
    finally:
        # 失败基线也必须清除本测试创建的凭据及进程。
        credential.unlink(missing_ok=True)
        for process in spawned:
            if process.returncode is None:
                process.kill()
                await process.wait()


class Listing:
    def __init__(self, rows, error=None):
        self.rows, self.error = rows, error

    async def collect(self):
        if self.error is not None:
            raise self.error
        return self.rows

    def __await__(self):
        return self.collect().__await__()

    def __aiter__(self):
        async def items():
            for row in await self.collect():
                yield row

        return items()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "modify, expected",
    [
        ("20260926010203", "2026-09-26T01:02:03+00:00"),
        ("20260926010203.125", "2026-09-26T01:02:03.125000+00:00"),
        ("20260926010203.123456789", "2026-09-26T01:02:03.123456+00:00"),
        (None, None),
        ("20261326010203", "invalid"),
        ("202609260102", "invalid"),
        ("", "invalid"),
    ],
)
async def test_ftp_mlsd_time_is_utc_iso(modify, expected, tmp_path):
    parser = aioftp.Client()
    facts = "type=file;size=5;" + (f"modify={modify};" if modify is not None else "")
    name, info = parser.parse_mlsx_line((facts + " fixture.txt\r\n").encode())

    class Client:
        def list(self, path, *, raw_command=None):
            return Listing([(PurePosixPath("/files") / name, info)])

    client = FtpFileClient(
        1,
        FtpFileClientConfig(
            base_path="/files",
            domain="http://testserver",
            host="127.0.0.1",
            port=21,
            username="fixture",
            password="fixture",
            mode="PASV",
        ),
    )
    await client.init()

    @asynccontextmanager
    async def connection():
        yield Client()

    client._client = connection
    if expected == "invalid":
        with pytest.raises(ValueError):
            await client.list_objects()
    else:
        rows = (await client.list_objects())["files"]
        assert rows[0]["lastModified"] == expected
        if modify == "20260926010203.125":
            (tmp_path / "ftp-wire-sample.json").write_text(json.dumps(rows), encoding="utf-8")


@pytest.mark.asyncio
async def test_ftp_list_fallback_keeps_unknown_timezone_and_rejects_permission_failure():
    parser = aioftp.Client()
    name, info = parser.parse_list_line(b"-rw-r--r-- 1 owner group 5 Sep 26  2026 fixture.txt\r\n")

    class Client:
        code = "502"

        def list(self, path, *, raw_command=None):
            if raw_command == "MLSD":
                return Listing(
                    [], aioftp.StatusCodeError("1xx", aioftp.Code(self.code), ["fixture response"])
                )
            return Listing([(PurePosixPath("/files") / name, info)])

    transport = Client()
    client = FtpFileClient(
        1,
        FtpFileClientConfig(
            base_path="/files",
            domain="http://testserver",
            host="127.0.0.1",
            port=21,
            username="fixture",
            password="fixture",
            mode="PASV",
        ),
    )
    await client.init()

    @asynccontextmanager
    async def connection():
        yield transport

    client._client = connection
    rows = (await client.list_objects())["files"]
    assert rows[0]["name"] == "fixture.txt"
    assert rows[0]["lastModified"] is None
    transport.code = "550"
    with pytest.raises(aioftp.StatusCodeError):
        await client.list_objects()


@pytest.mark.asyncio
async def test_ftp_real_mlsd_on_loopback(tmp_path):
    file = tmp_path / "fixture.txt"
    file.write_bytes(b"hello")
    timestamp = datetime(2026, 9, 26, 1, 2, 3, tzinfo=timezone.utc).timestamp()
    os.utime(file, (timestamp, timestamp))
    server = aioftp.Server([aioftp.User("fixture", "FixtureOnly123", base_path=tmp_path)])
    await server.start("127.0.0.1", 0)
    client = FtpFileClient(
        1,
        FtpFileClientConfig(
            base_path="/",
            domain="http://testserver",
            host="127.0.0.1",
            port=server.server.sockets[0].getsockname()[1],
            username="fixture",
            password="FixtureOnly123",
            mode="PASV",
        ),
    )
    try:
        await client.init()
        rows = (await client.list_objects())["files"]
        assert rows == [
            {
                "key": "fixture.txt",
                "name": "fixture.txt",
                "size": 5,
                "lastModified": "2026-09-26T01:02:03+00:00",
            }
        ]
    finally:
        await server.close()
