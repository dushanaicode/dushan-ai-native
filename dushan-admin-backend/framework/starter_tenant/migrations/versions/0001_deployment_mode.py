from alembic import op

from framework.starter_tenant.model.deployment_mode_record import DeploymentModeRecord

revision = "tenant_mode_0001"
down_revision = None
branch_labels = None
depends_on = None


class DeploymentModeMigration:
    @staticmethod
    def upgrade():
        DeploymentModeRecord.__table__.create(op.get_bind(), checkfirst=False)

    @staticmethod
    def downgrade():
        DeploymentModeRecord.__table__.drop(op.get_bind(), checkfirst=False)


def upgrade():
    DeploymentModeMigration.upgrade()


def downgrade():
    DeploymentModeMigration.downgrade()
