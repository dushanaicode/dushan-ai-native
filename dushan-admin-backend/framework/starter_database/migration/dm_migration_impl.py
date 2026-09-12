from alembic.ddl.impl import DefaultImpl


class DmMigrationImpl(DefaultImpl):
    """达梦原生 DDL 交给已安装方言编译，不承诺自动提交 DDL 可以回滚。"""

    __dialect__ = "dm"
    transactional_ddl = False
