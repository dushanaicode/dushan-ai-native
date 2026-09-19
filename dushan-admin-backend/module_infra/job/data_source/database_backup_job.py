import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from framework.common.exception import (
    IllegalArgumentException,
)
from framework.common.utils import CleanupUtils
from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.config.infra_backup_settings import InfraBackupSettings
from module_infra.job.data_source.database_backup_parameters import DatabaseBackupParameters
from module_infra.service.data_source.data_source_config_store import DataSourceConfigStore


@job(
    key="infra.database.backup",
    parameters=DatabaseBackupParameters,
    source="module_infra",
    capability="infra.database.backup",
)
class DatabaseBackupJob(JobHandler):
    settings: InfraBackupSettings = Inject()
    sources: DataSourceConfigStore = Inject()

    async def execute(self, parameters, context):
        if not self.settings.enabled:
            raise IllegalArgumentException(msg="数据库备份未启用")
        sources = {
            source.name: source
            for source in (*self.sources.settings.sources, *await self.sources.load_sources())
        }
        url = make_url(sources[self.settings.data_source].url.get_secret_value())
        if url.get_backend_name() not in {"mysql", "mariadb"}:
            raise IllegalArgumentException(msg="此备份处理器要求 MySQL 协议的数据源")
        if url.query:
            unsupported = set(url.query) - {"charset"}
            if unsupported:
                raise IllegalArgumentException(msg="备份连接参数必须由部署配置显式提供")
        cwd = Path.cwd().resolve()
        temporary = cwd / "Temp" / "infra-backup" / uuid4().hex
        temporary.mkdir(parents=True)
        credential = temporary / "client.cnf"
        # MySQL option file 支持双引号与反斜线转义；不把密码放进 argv 或日志。
        values = {
            "host": url.host or "localhost",
            "port": str(url.port or 3306),
            "user": url.username or "",
            "password": url.password or "",
        }
        credential.write_text(
            "[client]\n"
            + "".join(
                key + "=" + json.dumps(value, ensure_ascii=False) + "\n"
                for key, value in values.items()
            ),
            encoding="utf-8",
        )
        directory = Path(self.settings.output_directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (
            "backup-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid4().hex[:12]
            + ".sql"
        )
        arguments = [
            self.settings.executable,
            "--defaults-file=" + str(credential),
            "--no-login-paths",
            "--single-transaction",
            "--set-gtid-purged=OFF",
            "--routines",
            "--triggers",
            "--events",
        ]
        if parameters.backup_type == "incremental":
            arguments.extend(["--source-data=2", "--flush-logs"])
        arguments.extend(["--databases", "--", url.database])
        environment = dict(os.environ, **{key: str(temporary) for key in ("TEMP", "TMP", "TMPDIR")})
        process = None
        try:
            with target.open("xb") as output:
                process = await asyncio.create_subprocess_exec(
                    *arguments,
                    cwd=cwd,
                    env=environment,
                    stdout=output,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                try:
                    await asyncio.wait_for(process.communicate(), self.settings.timeout_seconds)
                except BaseException:
                    if process.returncode is None:
                        process.kill()
                    await CleanupUtils.run_cancellation_safe_cleanup(process.wait, "备份进程回收")
                    raise
                if process.returncode != 0:
                    raise OSError("mysqldump 退出码: " + str(process.returncode))
            if target.stat().st_size == 0:
                raise OSError("数据库备份为空")
            return str(target)
        except BaseException:
            # 保留失败产物用于调查，明确命名，不能被当作有效备份。
            if target.exists():
                target.rename(target.with_suffix(".failed.sql"))
            raise
        finally:
            credential.unlink(missing_ok=True)
