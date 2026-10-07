import argparse
import json
import secrets
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import bcrypt
import yaml


class Prepare:
    """生成独立部署的凭据、application 配置和仅供空库使用的初始化 SQL。"""

    @staticmethod
    def prepare(output: Path, origin: str) -> None:
        root = Path(__file__).resolve().parents[1]
        output = output.resolve()
        if not output.is_relative_to(Path.cwd().resolve() / "Temp"):
            raise ValueError("生成文件必须位于当前工作目录的 Temp/ 内")
        parsed = urlsplit(origin)
        if (
            any(character.isspace() for character in origin)
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("origin 必须是浏览器可访问的 HTTP(S) 站点源，不带路径或凭据")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("origin 端口必须在 1～65535 之间")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("非回环部署必须配置可信 HTTPS")
        origin = origin.rstrip("/")
        # 不覆盖既有目录，避免重生成凭据使持久数据库失联。
        output.mkdir(parents=True, exist_ok=False)
        output.chmod(0o700)
        for directory in ("secrets", "mysql-init", "application"):
            (output / directory).mkdir()
        passwords = {
            name: "Aa9!" + secrets.token_hex(18)
            for name in (
                "admin",
                "mysql-password",
                "mysql-root-password",
                "redis-password",
                "postgres-password",
                "rabbitmq-password",
                "minio-password",
                "ftp-password",
                "sftp-password",
                "grafana-password",
                "vendor-password",
            )
        }
        # 当前登录 VO 的密码上限为 16；保留大小写、数字和特殊字符。
        passwords["admin"] = "Aa9!" + secrets.token_urlsafe(9)
        passwords["vendor-password"] = "Aa9!" + secrets.token_hex(12)
        for name, value in passwords.items():
            Prepare.write(output / "secrets" / name, value)
        Prepare.write(
            output / "credentials.json",
            json.dumps({"admin_username": "admin", "origin": origin, **passwords}, indent=2),
        )
        Prepare.write(
            output / "redis.conf",
            "bind 0.0.0.0\nprotected-mode yes\nport 6379\ndir /data\n"
            "appendonly yes\nappendfsync everysec\nmaxmemory-policy noeviction\n"
            f"requirepass {passwords['redis-password']}\n",
        )
        Prepare.write(
            output / "rabbitmq.conf",
            f"default_user = dushan\ndefault_pass = {passwords['rabbitmq-password']}\n"
            "default_vhost = /\n",
        )
        Prepare.write(
            output / "minio.env",
            f"MINIO_ROOT_USER=nativeadmin\nMINIO_ROOT_PASSWORD={passwords['minio-password']}\n",
        )
        Prepare.write(
            output / "ftp.env",
            f"FTP_USER=dushan\nFTP_PASS={passwords['ftp-password']}\n",
        )
        Prepare.write(
            output / "sftp-users.conf",
            f"dushan:{passwords['sftp-password']}:1001:1001:upload\n",
        )
        vendor = passwords["vendor-password"]
        Prepare.write(
            output / "tidb-init.sql",
            f"ALTER USER 'root'@'%' IDENTIFIED BY '{vendor}';\nCREATE DATABASE native;\n",
        )
        for name, values in {
            "opengauss": {
                "GS_PASSWORD": vendor,
                "GS_DB": "postgres",
                "GS_USERNAME": "native",
                "GS_HOST_AUTH_METHOD": "md5",
            },
            "oceanbase": {"OB_TENANT_PASSWORD": vendor, "OB_SYS_PASSWORD": vendor},
            "kingbase": {"DB_PASSWORD": vendor, "DB_MODE": "pg", "DB_USER": "kingbase"},
            "dameng": {"SYSDBA_PWD": vendor, "SYSAUDITOR_PWD": vendor, "SYSSSO_PWD": vendor},
        }.items():
            Prepare.write(
                output / f"{name}.env", "".join(f"{key}={value}\n" for key, value in values.items())
            )
        Prepare.application(root, output, passwords, origin)
        Prepare.database(root, output, passwords, origin)
        print(f"已生成：{output}；凭据仅写入 credentials.json，未输出密码。")

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8", newline="\n")
        # Runtime 根目录仅属主可遍历；挂载后的文件允许容器非 root 用户读取。
        path.chmod(0o644)

    @staticmethod
    def application(root: Path, output: Path, passwords: dict[str, str], origin: str) -> None:
        backend = root / "dushan-admin-backend"
        config = yaml.safe_load((backend / "application.yaml").read_text(encoding="utf-8"))
        config["server"].update(host="0.0.0.0", port=48080, env="staging", reload=False)
        config["granian"]["workers"] = 1
        config["modules"]["enabled"] = ["framework", "system", "infra"]
        config["log"]["enable_file_overall"] = False
        config["banner"]["show_mascot"] = False
        config["expression"]["enabled"] = True
        models = config["config"]["models"]
        models["database"].update(
            enabled=True,
            dynamic_enabled=True,
            id_strategy="snowflake",
            snowflake_machine_id=201,
            sources=[
                {
                    "name": "primary",
                    "role": "primary",
                    "weight": 1,
                    "pool": None,
                    "tls": None,
                    "url": f"mysql+aiomysql://dushan:{passwords['mysql-password']}@mysql:3306/dushan_native",
                }
            ],
        )
        models["cache"].update(
            enabled=True, host="redis", port=6379, password=passwords["redis-password"]
        )
        models["security"].update(enabled=True, bizlog_enabled=True)
        models["data_permission"]["enabled"] = True
        models["protection"]["enabled"] = True
        models["job"].update(enabled=True, owner_enabled=True)
        models["mq"].update(enabled=True, backend="redis", signing_secret=secrets.token_hex(32))
        models["websocket"].update(enabled=True, transport="local", allowed_origins=[origin])
        models["system"].update(
            refresh_cookie_name="native_docker_refresh",
            default_password="Aa9!" + secrets.token_urlsafe(9),
            workload_credential=secrets.token_hex(32),
            message_signing_key=secrets.token_hex(32),
            sms_callback_token=secrets.token_hex(32),
            allowed_origins=[origin],
            refresh_cookie_secure=origin.startswith("https://"),
        )
        Prepare.write(
            output / "application" / "application.yaml",
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        )
        for profile in ("staging", "prod"):
            Prepare.write(
                output / "application" / f"application-{profile}.yaml",
                "server:\n  reload: false\n  debug: false\n"
                f"  docs_enabled: {'true' if profile == 'staging' else 'false'}\n",
            )

    @staticmethod
    def database(root: Path, output: Path, passwords: dict[str, str], origin: str) -> None:
        source = root / "dushan-admin-backend" / "sql" / "mysql"
        files = [
            *sorted((source / "system").glob("*.sql")),
            *sorted((source / "infra").glob("*.sql")),
        ]
        for index, path in enumerate(files):
            shutil.copyfile(path, output / "mysql-init" / f"{index:03d}_{path.name}")
        password_hash = bcrypt.hashpw(
            passwords["admin"].encode(), bcrypt.gensalt(rounds=12)
        ).decode()
        # 此文件只由 MySQL 空数据目录入口执行；既有库升级不得重跑初始化目录。
        disabled_hash = bcrypt.hashpw(
            secrets.token_urlsafe(24).encode(), bcrypt.gensalt(rounds=12)
        ).decode()
        sql_origin = origin.replace("'", "''")
        Prepare.write(
            output / "mysql-init" / "999_deployment_credentials.sql",
            f"UPDATE system_users SET password='{disabled_hash}', status=0;\n"
            f"UPDATE system_users SET password='{password_hash}', status=1 WHERE id=10100000010001;\n"
            f"UPDATE system_oauth2_client SET secret='{secrets.token_hex(32)}' WHERE client_id='default';\n"
            f"UPDATE system_tenant SET websites=JSON_ARRAY('{sql_origin}') WHERE id=1;\n"
            f"UPDATE infra_file_config SET config=JSON_SET(config, '$.domain', '{sql_origin}') WHERE storage=1;\n",
        )
        shutil.copyfile(
            root / "docker" / "db" / "mysql" / "mark-ready.sh",
            output / "mysql-init" / "zzz-ready.sh",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="准备 Native Docker 开发/预发布配置，不启动容器")
    parser.add_argument("--output", type=Path, default=Path.cwd() / "Temp" / "docker-runtime")
    parser.add_argument("--origin", default="http://localhost:18080")
    arguments = parser.parse_args()
    Prepare.prepare(arguments.output, arguments.origin)
