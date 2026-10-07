import pytest

from module_system.api.auth.workload_api import WorkloadApi
from module_system.api.auth.workload_api_impl import WorkloadApiImpl
from module_system.api.oauth2.oauth2_session_api import OAuth2SessionApi
from module_system.api.oauth2.oauth2_session_api_impl import OAuth2SessionApiImpl

pytestmark = pytest.mark.unit


class TestApiRuntimeContracts:
    @pytest.mark.parametrize(
        "protocol,implementation",
        [(WorkloadApi, WorkloadApiImpl), (OAuth2SessionApi, OAuth2SessionApiImpl)],
    )
    def test_runtime_protocol_accepts_implementation(self, protocol, implementation):
        assert isinstance(implementation(), protocol)
        assert not isinstance(object(), protocol)
