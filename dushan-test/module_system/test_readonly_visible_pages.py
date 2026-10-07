import json

import pytest
from test_readonly_seed import TestReadonlySeed as _ReadonlySeed


@pytest.mark.asyncio(loop_scope="class")
class TestReadonlyVisiblePages:
    readonly_database = _ReadonlySeed.readonly_database
    readonly_app = _ReadonlySeed.readonly_app
    demo_client = _ReadonlySeed.demo_client
    _cache_prefix = staticmethod(_ReadonlySeed._cache_prefix)

    # 首屏依赖包含挂载子组件；接口来自 src/api，并与后端 RoutePolicy 核对。
    PAGE_REQUESTS = {
        # 用户管理: views/system/user/index.vue
        "10000000000101": (
            "system/user/index",
            (
                ("/system/user/page", {"page": 1, "pageSize": 10}),
                ("/system/dept/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 角色管理: views/system/role/index.vue
        "10000000000201": (
            "system/role/index",
            (
                ("/system/permission/role/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 菜单管理: views/system/menu/index.vue
        "10000000000301": (
            "system/menu/index",
            (("/system/permission/menu/list", {}), ("/system/dict/data/simple-list", {})),
        ),
        # 部门管理: views/system/dept/index.vue
        "10000000000401": (
            "system/dept/index",
            (
                ("/system/dept/list", {}),
                ("/system/user/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 岗位管理: views/system/post/index.vue
        "10000000000501": (
            "system/post/index",
            (
                ("/system/dept/post/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 字典管理: views/system/dict/index.vue
        "10000000000601": (
            "system/dict/index",
            (
                ("/system/dict/type/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 通知管理: views/system/notification/notice/index.vue
        "10000000000711": (
            "system/notification/notice/index",
            (
                ("/system/notification/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 通知日志: views/system/notification/notice-log/index.vue
        "10000000000721": (
            "system/notification/notice-log/index",
            (
                ("/system/notification/log/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 系统公告: views/system/announcement/index.vue
        "10000000000741": (
            "system/announcement/index",
            (
                ("/system/announcement/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 邮箱账号: views/system/mail/account/index.vue
        "10000000001011": (
            "system/mail/account/index",
            (
                ("/system/mail/account/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 邮件模板: views/system/mail/template/index.vue
        "10000000001021": (
            "system/mail/template/index",
            (
                ("/system/mail/template/page", {"page": 1, "pageSize": 10}),
                ("/system/mail/account/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 邮件日志: views/system/mail/log/index.vue
        "10000000001031": (
            "system/mail/log/index",
            (
                ("/system/mail/log/page", {"page": 1, "pageSize": 10}),
                ("/system/mail/account/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 短信渠道: views/system/sms/channel/index.vue
        "10000000001111": (
            "system/sms/channel/index",
            (
                ("/system/sms/channel/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 短信模板: views/system/sms/template/index.vue
        "10000000001121": (
            "system/sms/template/index",
            (
                ("/system/sms/template/page", {"page": 1, "pageSize": 10}),
                ("/system/sms/channel/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 短信日志: views/system/sms/log/index.vue
        "10000000001131": (
            "system/sms/log/index",
            (
                ("/system/sms/log/page", {"page": 1, "pageSize": 10}),
                ("/system/sms/channel/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 租户列表: views/system/tenant/index.vue
        "10000000001201": (
            "system/tenant/index",
            (
                ("/system/tenant/page", {"page": 1, "pageSize": 10}),
                ("/system/tenant/package/simple-list", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 租户套餐: views/system/tenantPackage/index.vue
        "10000000001301": (
            "system/tenantPackage/index",
            (
                ("/system/tenant/package/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # OAuth2 客户端: views/system/oauth2/client/index.vue
        "10000000001411": (
            "system/oauth2/client/index",
            (
                ("/system/oauth2/client/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # OAuth2 令牌: views/system/oauth2/token/index.vue
        "10000000001421": (
            "system/oauth2/token/index",
            (
                ("/system/oauth2/token/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 社交客户端: views/system/social/client/index.vue
        "10000000001511": (
            "system/social/client/index",
            (
                ("/system/social/client/page", {"page": 1, "pageSize": 10}),
                ("/system/social/client/types", {}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 社交用户: views/system/social/user/index.vue
        "10000000001521": (
            "system/social/user/index",
            (
                ("/system/social/user/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 地区管理: views/system/area/index.vue
        "10000000001601": ("system/area/index", (("/system/area/tree", {}),)),
        # 登录日志: views/system/loginlog/index.vue
        "10000000001701": (
            "system/loginlog/index",
            (
                ("/system/logger/login-log/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 操作日志: views/system/operatelog/index.vue
        "10000000001801": (
            "system/operatelog/index",
            (("/system/logger/operate-log/page", {"page": 1, "pageSize": 10}),),
        ),
        # 配置管理: views/infra/config/index.vue
        "10000000100101": (
            "infra/config/index",
            (
                ("/infra/config/type/page", {"page": 1, "pageSize": 10}),
                ("/infra/config/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 文件空间: views/infra/file/index.vue
        "10000000100211": (
            "infra/file/index",
            (
                ("/infra/file/config/simple-list", {}),
                ("/infra/file/list-objects", {"configId": "10300000040001", "prefix": ""}),
            ),
        ),
        # 存储配置: views/infra/fileConfig/index.vue
        "10000000100221": (
            "infra/fileConfig/index",
            (
                ("/infra/file/config/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 定时任务: views/infra/job/index.vue
        "10000000100301": (
            "infra/job/index",
            (
                ("/infra/job/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 消息队列: views/infra/mq/index.vue
        "10000000100401": ("infra/mq/index", (("/infra/mq/page", {"page": 1, "pageSize": 10}),)),
        # 数据源配置: views/infra/dataSourceConfig/index.vue
        "10000000100501": (
            "infra/dataSourceConfig/index",
            (
                ("/infra/data-source/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 访问日志: views/infra/apiAccessLog/index.vue
        "10000000100611": (
            "infra/apiAccessLog/index",
            (
                ("/infra/logger/api-access-log/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 错误日志: views/infra/apiErrorLog/index.vue
        "10000000100621": (
            "infra/apiErrorLog/index",
            (
                ("/infra/logger/api-error-log/page", {"page": 1, "pageSize": 10}),
                ("/system/dict/data/simple-list", {}),
            ),
        ),
        # 服务监控: views/infra/server/index.vue
        "10000000100711": ("infra/server/index", (("/infra/server/list", {}),)),
        # Redis 监控: views/infra/redis-monitor/index.vue
        "10000000100721": ("infra/redis-monitor/index", (("/infra/cache/get-monitor-info", {}),)),
        # Redis 缓存: views/infra/redis-cache/index.vue
        "10000000100731": (
            "infra/redis-cache/index",
            (
                ("/infra/cache/monitor/db-list", {}),
                ("/infra/cache/monitor/get-names", {"page": 1, "pageSize": 10}),
            ),
        ),
        # 在线用户: views/infra/online/index.vue
        "10000000100741": (
            "infra/online/index",
            (("/infra/online/list", {"page": 1, "pageSize": 10}),),
        ),
        # WebSocket: views/infra/webSocket/index.vue
        "10000000100801": (
            "infra/webSocket/index",
            (("/infra/websocket/status", {}), ("/system/user/simple-list", {})),
        ),
        # 代码生成: views/infra/codegen/index.vue
        "10000000100901": (
            "infra/codegen/index",
            (
                ("/infra/codegen/table/page", {"page": 1, "pageSize": 10}),
                ("/infra/data-source/list-by-status", {"status": 1}),
                ("/infra/data-source/list-by-status", {"status": 0}),
            ),
        ),
        # API 文档：嵌入 HTML，无首屏业务数据 GET。
        "10000000101001": ("infra/docs/index", ()),
        # 监控面板: views/infra/monitor/index.vue
        "10000000101101": (
            "infra/monitor/index",
            (
                ("/infra/config/get-value-by-key", {"key": "url.jaeger"}),
                ("/infra/config/get-value-by-key", {"key": "url.tempo"}),
            ),
        ),
        # 表单构建：初始化本地设计器，无首屏业务数据 GET。
        "10000000101201": ("infra/build/index", ()),
    }
    BLOCKED_PAGES = {
        "10000000001031",
        "10000000001131",
        "10000000100101",
        "10000000100501",
        "10000000100731",
    }
    OWNER_PAGES = {"10000000000301", "10000000001201", "10000000001301"}

    async def test_visible_pages_initial_queries(self, demo_client, tmp_path):
        """使用真实菜单与令牌执行首屏查询，汇总所有失败页面。"""
        response = (await demo_client.get("/admin-api/system/auth/get-permission-info")).json()
        assert response["code"] == 0, response
        menus = list(response["data"]["menus"])
        visible_ids = set()
        page_ids = set()
        checks = []
        failures = []
        while menus:
            menu = menus.pop()
            visible_ids.add(str(menu["id"]))
            menus.extend(menu["children"] or [])
            if menu["kind"] != "page":
                continue
            page_ids.add(menu["id"])
            component, queries = self.PAGE_REQUESTS[menu["id"]]
            assert menu["component"] == component
            page_result = {"id": menu["id"], "name": menu["name"], "queries": []}
            checks.append(page_result)
            for path, params in queries:
                result = (await demo_client.get("/admin-api" + path, params=params)).json()
                page_result["queries"].append(
                    {"path": path, "params": params, "code": result["code"]}
                )
                if result["code"] != 0:
                    failures.append((menu["id"], menu["name"], path, result))
        (tmp_path / "visible-page-queries.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert not failures, failures
        assert not visible_ids.intersection(self.BLOCKED_PAGES)
        assert page_ids == self.PAGE_REQUESTS.keys() - self.BLOCKED_PAGES - self.OWNER_PAGES

    async def test_notice_log_detail_contains_message_fields(self, demo_client, readonly_database):
        """实际读取带消息的日志，校验属性转换、字符串 ID 和用户补全。"""
        _, _, connection, _ = readonly_database
        log_id = 10100000019001
        message_id = 10100000019002
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM system_users WHERE username = 'demo'")
            user_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO system_notification_notice_log "
                "(id, notice_id, notice_title, notice_type, push_target_type, push_channels, "
                "total_count, success_count, fail_count, push_status, tenant_id, creator, "
                "create_time, updater, update_time, deleted) VALUES "
                "(%s, %s, '通知详情回归', 1, 1, '[\"INTERNAL\"]', 1, 1, 0, 1, '1', 'test', "
                "'2026-10-01 08:00:00', 'test', '2026-10-01 08:00:00', 0)",
                (log_id, log_id),
            )
            cursor.execute(
                "INSERT INTO system_notification_message "
                "(id, user_id, user_type, notice_id, notice_log_id, notice_title, notice_content, "
                "notice_type, sent_channels, read_status, read_time, tenant_id, creator, "
                "create_time, updater, update_time, deleted) VALUES "
                "(%s, %s, 2, %s, %s, '通知详情回归', '消息正文', 1, '[\"INTERNAL\"]', 1, "
                "'2026-10-01 09:00:00', '1', 'test', '2026-10-01 08:00:00', "
                "'test', '2026-10-01 08:00:00', 0)",
                (message_id, user_id, log_id, log_id),
            )
        result = (
            await demo_client.get(
                "/admin-api/system/notification/log/get", params={"id": str(log_id)}
            )
        ).json()
        assert result["code"] == 0, result
        detail = result["data"]
        assert detail["id"] == str(log_id)
        assert detail["noticeTitle"] == "通知详情回归"
        assert detail["messages"] == [
            {
                "id": str(message_id),
                "userId": str(user_id),
                "username": "demo",
                "nickname": "演示用户",
                "userType": 2,
                "readStatus": True,
                "readTime": "2026-10-01T09:00:00",
                "createTime": "2026-10-01T08:00:00",
            }
        ]
