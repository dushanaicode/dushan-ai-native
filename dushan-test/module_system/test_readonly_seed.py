import json
import os
from functools import partial
from pathlib import Path
from uuid import uuid4

import pymysql
import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient, BasicAuth
from pymysql.constants import CLIENT
from redis import Redis

from fixtures.config_factory import ConfigFactory
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_security.public import OpaqueToken, SecurityErrorCodes
from server.starter_server import StarterServer


@pytest.mark.asyncio(loop_scope="class")
class TestReadonlySeed:
    READ_ACTIONS = {"query", "list", "page", "preview", "get-monitor-info"}
    BLOCKED_PERMISSIONS = {
        "infra:config:query",
        "infra:data-source:query",
        "system:sms:log:query",
        "system:mail:log:query",
        "infra:cache:get-names",
    }
    OWNER_ONLY_PERMISSIONS = {
        "system:permission:menu:query",
        "system:tenant:query",
        "system:tenant:package:query",
    }

    @pytest.fixture(scope="class", params=["module_order", "docker_order"])
    @classmethod
    def readonly_database(cls, request):
        """在独立测试库实际执行全部结构及种子，并验证两种现行导入顺序。"""
        root = Path(__file__).resolve().parents[2]
        resource_value = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
        if resource_value is None:
            pytest.skip("需要本轮独立 MySQL/Redis 资源清单 DUSHAN_SYSTEM_RESOURCES")
        resources = json.loads(Path(resource_value).read_text(encoding="utf-8"))
        assert Path(resources["mysql_datadir"]).resolve().is_relative_to(root / "Temp")
        sql_root = root / "dushan-admin-backend/sql/mysql"
        sql_files = [
            *sorted((sql_root / "system").glob("*.sql")),
            *sorted((sql_root / "infra").glob("*.sql")),
        ]
        if request.param == "docker_order":
            sql_files = [
                *sorted(path for path in sql_files if path.name.startswith("00_")),
                *sorted(path for path in sql_files if not path.name.startswith("00_")),
            ]
        connection = pymysql.connect(
            host="127.0.0.1",
            port=resources["mysql_port"],
            user="root",
            password="",
            autocommit=True,
            charset="utf8mb4",
            client_flag=CLIENT.MULTI_STATEMENTS,
        )
        name = os.environ.get("DUSHAN_TEST_DATABASE_PREFIX", "readonly_seed_") + uuid4().hex
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT @@datadir, @@port")
                data_dir, port = cursor.fetchone()
                assert Path(data_dir).resolve() == Path(resources["mysql_datadir"]).resolve()
                assert port == resources["mysql_port"]
                cursor.execute(
                    f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                cursor.execute(f"USE `{name}`")
                for path in sql_files:
                    cursor.execute(path.read_text(encoding="utf-8"))
                    while cursor.nextset():
                        pass
            yield resources, name, connection, sql_files
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
            connection.close()

    @pytest_asyncio.fixture(scope="class", loop_scope="class")
    @classmethod
    async def readonly_app(cls, readonly_database, tmp_path_factory):
        """启动真实鉴权应用，仅给缓存键增加随机前缀以隔离并行种子账号。"""
        resources, name, _, _ = readonly_database
        values = ConfigFactory.values()
        folder = tmp_path_factory.mktemp("readonly-config")
        values["modules"]["enabled"] = ["framework", "system", "infra"]
        values["server"]["reload"] = False
        values["log"].update(enable_file_overall=False, console_level="WARNING")
        models = values["config"]["models"]
        models["database"].update(
            enabled=True,
            health_check_enabled=False,
            id_strategy="snowflake",
            snowflake_machine_id=933,
            sources=[
                dict(
                    name="primary",
                    url=f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{name}?charset=utf8mb4",
                    role="primary",
                    weight=100,
                    pool=None,
                    tls=None,
                )
            ],
        )
        models["security"].update(enabled=True, permission_cache_enabled=False)
        models["data_permission"].update(enabled=True, cache_enabled=False)
        models["cache"].update(enabled=True, host="127.0.0.1", port=resources["redis_port"])
        models["ip"].update(enabled=True, local_enabled=False)
        models["protection"]["enabled"] = True
        models["qr_login"]["enabled"] = False
        models["system"].update(
            workload_credential=uuid4().hex + uuid4().hex,
            message_signing_key=uuid4().hex + uuid4().hex,
            sms_callback_token=uuid4().hex + uuid4().hex,
            refresh_cookie_secure=False,
            allowed_origins=["http://testserver"],
        )
        (folder / "application.yaml").write_text(
            yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
        )
        namespace = "readonly-seed:" + uuid4().hex + ":"
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                CacheKeyResolver,
                "build_prefix",
                staticmethod(partial(cls._cache_prefix, namespace, CacheKeyResolver.build_prefix)),
            )
            with Redis(host="127.0.0.1", port=resources["redis_port"]) as redis:
                assert redis.config_get("dir")["dir"] == resources["redis_dir"]
                try:
                    app = StarterServer.create_app(base_dir=folder, app_env="dev", environ={})
                    async with app.router.lifespan_context(app):
                        yield app
                finally:
                    for prefix in (
                        namespace,
                        "cache_generation:prefix:" + namespace,
                        "lock:cache_lock:default:" + namespace,
                        "lock:" + namespace,
                    ):
                        for key in redis.scan_iter(match=prefix + "*"):
                            redis.delete(key)

    @staticmethod
    def _cache_prefix(namespace, original, cache_key):
        """保留真实缓存租户分区规则，仅增加本次测试的唯一外层命名空间。"""
        return namespace + original(cache_key)

    @pytest_asyncio.fixture(scope="class", loop_scope="class")
    @classmethod
    async def demo_client(cls, readonly_app):
        """使用公开演示密码完成真实登录，再携带服务端签发的令牌。"""
        async with AsyncClient(
            transport=ASGITransport(app=readonly_app), base_url="http://testserver"
        ) as client:
            result = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "demo", "password": "demo123456"},
                    headers={"X-Tenant-Id": "1"},
                )
            ).json()
            assert result["code"] == 0, result
            assert result["data"]["tenantId"] == "1"
            client.headers["Authorization"] = "Bearer " + result["data"]["accessToken"]
            yield client

    @pytest_asyncio.fixture(scope="class", loop_scope="class")
    @classmethod
    async def readonly_admin_client(cls, readonly_app):
        """使用种子管理员令牌验证正常写入及角色授权。"""
        async with AsyncClient(
            transport=ASGITransport(app=readonly_app), base_url="http://testserver"
        ) as client:
            result = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "admin", "password": "admin123"},
                    headers={"X-Tenant-Id": "1"},
                )
            ).json()
            assert result["code"] == 0, result
            client.headers["Authorization"] = "Bearer " + result["data"]["accessToken"]
            yield client

    @staticmethod
    def _demo_profile_state(connection):
        """读取拒写前后的账号和个人资料，确认保护发生在持久化之前。"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password, nickname, mobile, avatar, credential_revision "
                "FROM system_users WHERE username = 'demo' AND deleted = 0"
            )
            account = cursor.fetchone()
            cursor.execute(
                "SELECT p.* FROM system_user_profiles p JOIN system_users u ON u.id = p.user_id "
                "WHERE u.username = 'demo' AND u.deleted = 0"
            )
            return account, cursor.fetchall()

    async def test_demo_identity_and_readonly_role_are_seeded(self, readonly_database):
        """演示账号、昵称、租户和唯一只读角色由初始化 SQL 提供。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.username, u.nickname, u.tenant_id, r.code, r.name, r.tenant_id "
                "FROM system_users u JOIN system_user_role ur ON ur.user_id = u.id "
                "JOIN system_role r ON r.id = ur.role_id "
                "WHERE u.username = 'demo' AND u.deleted = 0 "
                "AND ur.deleted = 0 AND r.deleted = 0"
            )
            assert cursor.fetchall() == (("demo", "演示用户", "1", "readonly", "只读演示", "1"),)

    async def test_common_and_readonly_grant_accessible_pages_and_safe_reads(
        self, readonly_database
    ):
        """普通与只读角色只授予可查询的页面及其安全按钮，保留菜单的父级必须获授权。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, parent_id, kind, permission FROM system_menu WHERE deleted = 0"
            )
            menus = cursor.fetchall()
            blocked_pages = {
                parent_id
                for _, parent_id, _, permission in menus
                if permission in self.BLOCKED_PERMISSIONS
            }
            assert len(blocked_pages) == 5
            expected = {
                menu_id
                for menu_id, parent_id, kind, permission in menus
                if menu_id not in blocked_pages
                and parent_id not in blocked_pages
                and (
                    kind in {"group", "page"}
                    or (
                        permission.rsplit(":", 1)[-1] in self.READ_ACTIONS
                        and permission not in self.BLOCKED_PERMISSIONS
                    )
                )
            }
            assert len(expected) == 85
            assert (
                sum(
                    menu_id in expected and kind in {"group", "page"}
                    for menu_id, _, kind, _ in menus
                )
                == 49
            )
            for role in ("common", "readonly"):
                cursor.execute(
                    "SELECT rm.menu_id FROM system_role_menu rm "
                    "JOIN system_role r ON r.id = rm.role_id "
                    "WHERE r.code = %s AND r.tenant_id = '1' "
                    "AND rm.tenant_id = '1' AND rm.deleted = 0 AND r.deleted = 0",
                    (role,),
                )
                grants = [row[0] for row in cursor.fetchall()]
                assert set(grants) == expected, role
                assert len(grants) == len(expected), role
                assert all(
                    parent_id == 0 or parent_id in grants
                    for menu_id, parent_id, _, _ in menus
                    if menu_id in grants
                ), role
                assert all(
                    any(
                        child_parent_id == menu_id and child_id in grants
                        for child_id, child_parent_id, _, _ in menus
                    )
                    for menu_id, _, kind, _ in menus
                    if menu_id in grants and kind == "group"
                ), role

    async def test_demo_login_exposes_only_read_permissions(self, demo_client, readonly_database):
        """真实权限接口只返回只读角色和已授权查询码，且用户查询可调用。"""
        response = (await demo_client.get("/admin-api/system/auth/get-permission-info")).json()
        assert response["code"] == 0, response
        info = response["data"]
        assert info["user"]["username"] == "demo"
        assert info["user"]["nickname"] == "演示用户"
        assert info["tenantId"] == "1"
        assert info["roles"] == ["readonly"]
        permissions = set(info["permissions"])
        assert permissions
        assert all(code.rsplit(":", 1)[-1] in self.READ_ACTIONS for code in permissions)
        assert not permissions.intersection(self.BLOCKED_PERMISSIONS)
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT m.permission FROM system_menu m "
                "JOIN system_role_menu rm ON rm.menu_id = m.id "
                "JOIN system_role r ON r.id = rm.role_id "
                "WHERE r.code = 'readonly' AND m.permission <> '' "
                "AND m.deleted = 0 AND rm.deleted = 0 AND r.deleted = 0"
            )
            assert (
                permissions == {row[0] for row in cursor.fetchall()} - self.OWNER_ONLY_PERMISSIONS
            )
        query = (await demo_client.get("/admin-api/system/user/page")).json()
        assert query["code"] == 0, query

    async def test_demo_cannot_create_role(self, demo_client, readonly_database):
        """只读角色在业务权限判断前拒绝写请求，数据库没有产生角色。"""
        code = "readonly_must_not_create"
        response = await demo_client.post(
            "/admin-api/system/permission/role/create",
            json={"name": "禁止创建", "code": code, "sort": 1},
        )
        assert response.json()["code"] == 901, response.json()
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM system_role WHERE code = %s", (code,))
            assert cursor.fetchone() == (0,)

    async def test_demo_cannot_trigger_data_source_connection(self, demo_client):
        """数据源查询码同时控制连接测试，因此演示角色不得获得该权限。"""
        response = await demo_client.post(
            "/admin-api/infra/data-source/test", params={"id": "10200000010001"}
        )
        assert response.json()["code"] == 901, response.json()

    async def test_oauth2_client_queries_do_not_return_seeded_secret(
        self, demo_client, readonly_database
    ):
        """已有客户端种子的真实密钥不得经获准的详情或列表接口泄露。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, secret FROM system_oauth2_client WHERE client_id = 'default'"
            )
            client_id, secret = cursor.fetchone()
        detail = await demo_client.get(
            "/admin-api/system/oauth2/client/get", params={"id": str(client_id)}
        )
        page = await demo_client.get("/admin-api/system/oauth2/client/page")
        for response in (detail, page):
            assert response.json()["code"] == 0, response.json()
            assert secret not in response.text
        assert "secret" not in detail.json()["data"]
        assert all("secret" not in row for row in page.json()["data"]["items"])

    @pytest.mark.parametrize(
        ("locale", "message"),
        [
            ("zh-CN", "演示账号只能查看，不能修改"),
            ("en-US", "Demo accounts can only view data, not modify it"),
        ],
    )
    async def test_demo_cannot_update_personal_profile(
        self, demo_client, readonly_database, locale, message
    ):
        """只需登录的个人资料入口也必须拒绝只读账号写入。"""
        _, _, connection, _ = readonly_database
        before = self._demo_profile_state(connection)
        response = await demo_client.put(
            "/admin-api/system/user/profile/update",
            json={"nickname": "不应保存", "bio": "不应新增个人资料"},
            headers={"Accept-Language": locale},
        )
        assert response.json()["code"] == 901, response.json()
        assert response.json()["message"] == message
        assert self._demo_profile_state(connection) == before

    async def test_demo_cannot_update_password(self, demo_client, readonly_database):
        """提供正确旧密码也不能修改演示密码，密码和凭据版本均不改变。"""
        _, _, connection, _ = readonly_database
        before = self._demo_profile_state(connection)
        response = await demo_client.put(
            "/admin-api/system/user/profile/update-password",
            json={"oldPassword": "demo123456", "newPassword": "changed123456"},
        )
        assert response.json()["code"] == 901, response.json()
        assert self._demo_profile_state(connection) == before

    async def test_demo_cannot_upload_avatar(self, demo_client, readonly_database):
        """业务头像上传在解析 multipart 和存储文件前拒绝。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM infra_file")
            before = cursor.fetchone()
        response = await demo_client.post(
            "/admin-api/infra/file/business-upload",
            data={"usage": "avatar"},
            files={"file": ("demo.png", b"readonly-avatar", "image/png")},
        )
        assert response.json()["code"] == 901, response.json()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM infra_file")
            assert cursor.fetchone() == before

    async def test_demo_cannot_bind_mobile(self, demo_client, readonly_database):
        """登录即用的绑定接口不得改变演示手机号。"""
        _, _, connection, _ = readonly_database
        before = self._demo_profile_state(connection)
        response = await demo_client.post(
            "/admin-api/system/auth/bind-mobile",
            json={"mobile": "13800138999", "code": "123456"},
        )
        assert response.json()["code"] == 901, response.json()
        assert self._demo_profile_state(connection) == before

    @pytest.mark.parametrize(
        "path",
        ["register", "reset-password", "send-password-reset-code", "send-bind-mobile-code"],
    )
    async def test_auth_prefix_does_not_bypass_readonly_guard(self, demo_client, path):
        """认证前缀下未列入白名单的请求仍在正文校验之前被拒绝。"""
        response = await demo_client.post(
            f"/admin-api/system/auth/{path}",
            json={},
            headers={"X-Tenant-Id": "1"} if path != "send-bind-mobile-code" else {},
        )
        assert response.json()["code"] == 901, response.json()

    async def test_basic_client_can_check_demo_token(self, demo_client, readonly_database):
        """公开 OAuth2 接口继续由 Basic 客户端认证，不误判为演示账号写操作。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT client_id, secret FROM system_oauth2_client WHERE client_id = 'default'"
            )
            client_id, secret = cursor.fetchone()
        token = demo_client.headers["Authorization"].removeprefix("Bearer ")
        response = await demo_client.post(
            "/admin-api/system/oauth2/open/check-token",
            params={"token": token},
            auth=BasicAuth(client_id, secret),
        )
        assert response.json()["code"] == 0, response.json()
        assert response.json()["data"]["clientId"] == client_id
        assert response.json()["data"]["accessToken"] == token

    async def test_demo_can_refresh_and_logout(self, readonly_app, readonly_database):
        """演示会话允许再次登录、有效或过期 Bearer 刷新及登出。"""
        async with AsyncClient(
            transport=ASGITransport(app=readonly_app),
            base_url="http://testserver",
            headers={"X-Tenant-Id": "1", "Origin": "http://testserver"},
        ) as client:
            login = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "demo", "password": "demo123456"},
                )
            ).json()
            assert login["code"] == 0, login
            client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
            second_login = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "demo", "password": "demo123456"},
                )
            ).json()
            assert second_login["code"] == 0, second_login
            client.headers["Authorization"] = "Bearer " + second_login["data"]["accessToken"]
            client.headers.pop("X-Tenant-Id")
            refreshed = (await client.post("/admin-api/system/auth/refresh-token")).json()
            assert refreshed["code"] == 0, refreshed
            assert refreshed["data"]["accessToken"] != second_login["data"]["accessToken"]
            client.headers["Authorization"] = "Bearer " + refreshed["data"]["accessToken"]
            assert (await client.get("/admin-api/system/user/profile/get")).json()["code"] == 0
            _, _, connection, _ = readonly_database
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE system_oauth2_access_token SET expires_time = '2000-01-01 00:00:00' "
                    "WHERE token_digest = %s",
                    (OpaqueToken.digest(refreshed["data"]["accessToken"]),),
                )
                assert cursor.rowcount == 1
            expired = (await client.get("/admin-api/system/user/profile/get")).json()
            assert expired["code"] == SecurityErrorCodes.EXPIRED.code, expired
            renewed = (await client.post("/admin-api/system/auth/refresh-token")).json()
            assert renewed["code"] == 0, renewed
            assert renewed["data"]["accessToken"] != refreshed["data"]["accessToken"]
            client.headers["Authorization"] = "Bearer " + renewed["data"]["accessToken"]
            logout = (await client.post("/admin-api/system/auth/logout")).json()
            assert logout["code"] == 0, logout
            assert (await client.get("/admin-api/system/user/profile/get")).json()["code"] != 0

    async def test_admin_can_update_profile_and_create_role(
        self, readonly_admin_client, readonly_database
    ):
        """管理员可以持久化个人资料和创建角色。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute("SELECT nickname FROM system_users WHERE username = 'admin'")
            original_nickname = cursor.fetchone()[0]
        response = await readonly_admin_client.put(
            "/admin-api/system/user/profile/update", json={"nickname": "管理员写入验证"}
        )
        assert response.json()["code"] == 0, response.json()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nickname FROM system_users WHERE username = 'admin'")
                assert cursor.fetchone() == ("管理员写入验证",)
            created = (
                await readonly_admin_client.post(
                    "/admin-api/system/permission/role/create",
                    json={"name": "可写验证角色", "code": "readonly_check_admin_write", "sort": 1},
                )
            ).json()
            assert created["code"] == 0, created
            with connection.cursor() as cursor:
                cursor.execute("SELECT code FROM system_role WHERE id = %s", (created["data"],))
                assert cursor.fetchone() == ("readonly_check_admin_write",)
        finally:
            restored = await readonly_admin_client.put(
                "/admin-api/system/user/profile/update", json={"nickname": original_nickname}
            )
            assert restored.json()["code"] == 0, restored.json()

    async def test_readonly_role_restricts_other_accounts_after_grant(
        self, readonly_app, readonly_admin_client, readonly_database
    ):
        """给非 demo 账号增加只读角色后立即阻止写入，撤销后恢复原权限。"""
        _, _, connection, _ = readonly_database
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nickname FROM system_users WHERE username = 'dushan'")
            user_id, nickname = cursor.fetchone()
            cursor.execute("SELECT id FROM system_role WHERE code = 'readonly'")
            readonly_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT role_id FROM system_user_role WHERE user_id = %s AND deleted = 0",
                (user_id,),
            )
            original_role_ids = [str(row[0]) for row in cursor.fetchall()]
        async with AsyncClient(
            transport=ASGITransport(app=readonly_app), base_url="http://testserver"
        ) as client:
            login = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "dushan", "password": "admin123"},
                    headers={"X-Tenant-Id": "1"},
                )
            ).json()
            assert login["code"] == 0, login
            client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
            before_grant = await client.put(
                "/admin-api/system/user/profile/update", json={"nickname": nickname}
            )
            assert before_grant.json()["code"] == 0, before_grant.json()
            granted = await readonly_admin_client.post(
                "/admin-api/system/permission/assign-user-role",
                json={"userId": str(user_id), "roleIds": [*original_role_ids, str(readonly_id)]},
            )
            assert granted.json()["code"] == 0, granted.json()
            try:
                response = await client.put(
                    "/admin-api/system/user/profile/update", json={"nickname": "不应写入其他账号"}
                )
                assert response.json()["code"] == 901, response.json()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT nickname FROM system_users WHERE id = %s", (user_id,))
                    assert cursor.fetchone() == (nickname,)
            finally:
                restored = await readonly_admin_client.post(
                    "/admin-api/system/permission/assign-user-role",
                    json={"userId": str(user_id), "roleIds": original_role_ids},
                )
                assert restored.json()["code"] == 0, restored.json()
            after_revoke = await client.put(
                "/admin-api/system/user/profile/update", json={"nickname": nickname}
            )
            assert after_revoke.json()["code"] == 0, after_revoke.json()

    async def test_seed_replay_does_not_duplicate_demo_or_grants(self, readonly_database):
        """重放全部种子后账号和关系行保持不变。"""
        _, _, connection, sql_files = readonly_database
        queries = (
            "SELECT id, username FROM system_users WHERE username = 'demo'",
            "SELECT id, code FROM system_role WHERE code IN ('common', 'readonly') ORDER BY id",
            "SELECT id, user_id, role_id FROM system_user_role ORDER BY id",
            "SELECT id, role_id, menu_id, tenant_id FROM system_role_menu ORDER BY id",
        )
        with connection.cursor() as cursor:
            before = []
            for query in queries:
                cursor.execute(query)
                before.append(cursor.fetchall())
            assert before[0]
            for path in sql_files:
                if not path.name.startswith("00_"):
                    cursor.execute(path.read_text(encoding="utf-8"))
                    while cursor.nextset():
                        pass
            for query, expected in zip(queries, before, strict=True):
                cursor.execute(query)
                assert cursor.fetchall() == expected
