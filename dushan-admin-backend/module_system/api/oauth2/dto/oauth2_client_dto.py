from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class OAuth2ClientDTO(BaseDTO):
    """OAuth2.0 客户端 DTO"""

    id: int
    client_id: Annotated[str, Field(..., description="客户端编号")]
    secret: Annotated[str | None, Field(None, description="客户端密钥")]
    name: Annotated[str, Field(..., description="应用名")]
    logo: Annotated[str, Field(..., description="应用图标")]
    description: Annotated[str | None, Field(None, description="应用描述")]
    status: Annotated[int, Field(..., description="状态")]
    user_type: int | None = None
    access_token_validity_seconds: Annotated[int, Field(..., description="访问令牌有效期")]
    refresh_token_validity_seconds: Annotated[int, Field(..., description="刷新令牌有效期")]
    redirect_uris: Annotated[list[str], Field(default_factory=list, description="重定向 URI 列表")]
    authorized_grant_types: Annotated[
        list[str], Field(default_factory=list, description="授权类型列表")
    ]
    scopes: Annotated[list[str], Field(default_factory=list, description="授权范围列表")]
    auto_approve_scopes: Annotated[
        list[str] | None, Field(default_factory=list, description="自动批准的授权范围列表")
    ]
    additional_information: Annotated[str | None, Field("", description="附加信息")]

    credential_revision: int
    authorities: list[str] | None = None
    resource_ids: list[str] | None = None
