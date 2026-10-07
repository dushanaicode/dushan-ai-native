from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.dal.mapper.tenant.tenant_mapper import TenantMapper


class TestTenantWebsiteLookup:
    @staticmethod
    def _tenant(identifier, websites):
        """构造包含真实 JSON 数组的租户记录。"""
        return TenantDO(
            id=identifier,
            name=f"租户{identifier}",
            contact_name="管理员",
            package_id=1,
            account_count=1,
            websites=websites,
            create_time=datetime(2026, 10, 5),
            update_time=datetime(2026, 10, 5),
        )

    @pytest_asyncio.fixture
    async def tenant_query(self):
        """在真实 SQLite JSON 列上执行 Mapper 查询，不依赖厂商 JSON 函数。"""
        engine = create_async_engine("sqlite+aiosqlite://")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(TenantDO.__table__.create)
            async with AsyncSession(engine) as session:
                session.add_all(
                    [
                        self._tenant(1, ["https://example.test", r"https://例子.test/a%_\'b"]),
                        self._tenant(2, []),
                        self._tenant(3, None),
                    ]
                )
                await session.commit()
                mapper = TenantMapper()
                mapper.read = session.execute
                yield mapper, session
        finally:
            await engine.dispose()

    @pytest.mark.parametrize(
        "website, expected",
        [
            ("https://example.test", 1),
            (r"https://例子.test/a%_\'b", 1),
            ("example.test", None),
            ("https://EXAMPLE.test", None),
            ("https://missing.test", None),
            ("", None),
        ],
    )
    async def test_exact_json_array_membership(self, tenant_query, website, expected):
        """域名精确、区分大小写匹配，不将子串或特殊字符当成 SQL 模式。"""
        mapper, _ = tenant_query
        tenant = await mapper.select_by_website(website)
        assert (tenant.id if tenant is not None else None) == expected

    async def test_duplicate_domain_remains_an_error(self, tenant_query):
        """重复绑定不静默选取其中一个租户，保持原查询的唯一结果契约。"""
        mapper, session = tenant_query
        session.add(self._tenant(4, ["https://example.test"]))
        await session.commit()
        with pytest.raises(MultipleResultsFound):
            await mapper.select_by_website("https://example.test")
