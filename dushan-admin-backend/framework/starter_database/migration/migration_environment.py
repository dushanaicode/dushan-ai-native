from alembic import context


class MigrationEnvironment:
    """Alembic 标准入口只消费调用方显式提供的连接或离线方言。"""

    @staticmethod
    def run() -> None:
        attributes = context.config.attributes
        options = {
            "target_metadata": attributes["target_metadata"],
            "version_table": attributes["version_table"],
            "compare_type": True,
            "transaction_per_migration": True,
        }
        if context.is_offline_mode():
            options.update(dialect_name=attributes["dialect_name"], literal_binds=True)
        else:
            options["connection"] = attributes["connection"]
        context.configure(**options)
        with context.begin_transaction():
            context.run_migrations()
