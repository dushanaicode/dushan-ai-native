from sqlalchemy import JSON, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class OAuth2ClientDO(GlobalControlDO):
    __tablename__ = "system_oauth2_client"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "OAuth2 客户端表"}},)

    client_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="客户端编号"
    )
    secret: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端密钥")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="应用名")
    logo: Mapped[str] = mapped_column(String(255), nullable=False, comment="应用图标")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="应用描述")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="状态")
    user_type: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="绑定的用户类型"
    )
    access_token_validity_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="访问令牌的有效期"
    )
    refresh_token_validity_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="刷新令牌的有效期"
    )
    redirect_uris: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, comment="可重定向的 URI 地址 (JSON 数组)"
    )
    authorized_grant_types: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, comment="授权类型 (JSON 数组)"
    )
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="授权范围 (JSON 数组)"
    )
    auto_approve_scopes: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="自动通过的授权范围 (JSON 数组)"
    )
    authorities: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="权限 (JSON 数组)"
    )
    resource_ids: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="资源 (JSON 数组)"
    )
    additional_information: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="附加信息"
    )

    credential_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="???????"
    )
