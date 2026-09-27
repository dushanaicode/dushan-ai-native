from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from module_system.dal.mapper.oauth2.oauth2_client_mapper import OAuth2ClientMapper

pytestmark = pytest.mark.unit


async def test_oauth_client_projection_preserves_credential_revision():
    row = SimpleNamespace(
        id=101,
        client_id="inspection-client",
        secret="test-only",
        name="客户端",
        logo="",
        description=None,
        status=1,
        user_type=2,
        credential_revision=17,
        access_token_validity_seconds=3600,
        refresh_token_validity_seconds=7200,
        redirect_uris=[],
        authorized_grant_types=["client_credentials"],
        scopes=[],
        auto_approve_scopes=[],
        authorities=[],
        resource_ids=[],
        additional_information="",
    )
    mapper = OAuth2ClientMapper()
    mapper.select_by_client_id = AsyncMock(return_value=row)
    result = await mapper.select_details_dto_by_client_id(row.client_id)
    assert result.credential_revision == 17
    assert result.client_id == row.client_id


async def test_missing_oauth_client_projection_stays_none():
    mapper = OAuth2ClientMapper()
    mapper.select_by_client_id = AsyncMock(return_value=None)
    assert await mapper.select_details_dto_by_client_id("missing") is None
