from framework.starter_database.migration.migration_environment import MigrationEnvironment

# Alembic 按 env_py 加载此协议入口；普通包扫描和导入不得运行迁移。
if __name__ == "env_py":
    MigrationEnvironment.run()
