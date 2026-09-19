import asyncio
import inspect
import json
from urllib.parse import parse_qs

import httpx
import pytest

from framework.starter_captcha.definitions.constants.captcha_error_codes import (
    CaptchaErrorCodes as Codes,
)
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.provider.aliyun_captcha_provider import AliyunCaptchaProvider
from framework.starter_captcha.provider.captcha_http_client import CaptchaHttpClient
from framework.starter_captcha.provider.tencent_captcha_provider import TencentCaptchaProvider


@pytest.fixture
def cloud_settings(settings):
    return settings(
        aliyun={
            "access_key_id": "test-id",
            "access_key_secret": "test-secret",
            "scene_id": "test-scene",
            "prefix": "test-prefix",
        },
        tencent={
            "app_id": 123456,
            "app_secret": "test-app-secret",
            "secret_id": "test-id",
            "secret_key": "test-secret",
        },
    )


@pytest.fixture
async def http_client(cloud_settings):
    client = CaptchaHttpClient(cloud_settings)
    yield client
    await client.close()
    assert client.client.is_closed


async def mocked(client, handler):
    async def streaming(request):
        response = handler(request)
        if inspect.isawaitable(response):
            response = await response
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            stream=httpx.ByteStream(response.content),
        )

    await client.client.aclose()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(streaming))


@pytest.mark.parametrize("parameter", ['{"sceneId":"opaque","data":"a +/="}', "eyJjZXopaque=="])
async def test_aliyun_opaque_parameter_and_bound_scene(cloud_settings, http_client, parameter):
    def reply(request):
        assert request.url.scheme == "https" and request.method == "POST"
        assert not request.url.query
        assert parse_qs(request.content.decode()) == {
            "CaptchaVerifyParam": [parameter],
            "SceneId": ["test-scene"],
        }
        assert request.headers["x-acs-version"] == "2023-03-05"
        assert request.headers["x-acs-action"] == "VerifyIntelligentCaptcha"
        assert request.headers["authorization"].startswith("ACS3-HMAC-SHA256 Credential=test-id,")
        return httpx.Response(200, json={"Success": True, "Result": {"VerifyResult": True}})

    await mocked(http_client, reply)
    provider = AliyunCaptchaProvider(cloud_settings.aliyun, http_client)
    data, record = provider.create("register")
    assert set(data) == {"scene_id", "prefix", "region", "language"}
    assert await provider.verify(record, CaptchaAnswer(captcha_verify_param=parameter), None)


@pytest.mark.parametrize(
    "response,code",
    [
        ({"Success": True, "Result": {"VerifyResult": False}}, None),
        ({"Success": False}, Codes.PROVIDER_FAILURE),
        ({"Success": "true", "Result": {"VerifyResult": True}}, Codes.PROVIDER_RESPONSE),
        ({"Success": True, "Result": {"VerifyResult": 1}}, Codes.PROVIDER_RESPONSE),
        ({"Success": True}, Codes.PROVIDER_RESPONSE),
    ],
)
async def test_aliyun_response_semantics(cloud_settings, http_client, response, code):
    await mocked(http_client, lambda request: httpx.Response(200, json=response))
    provider = AliyunCaptchaProvider(cloud_settings.aliyun, http_client)
    _, record = provider.create("login")
    if code is None:
        assert (
            await provider.verify(record, CaptchaAnswer(captcha_verify_param="opaque"), None)
            is False
        )
    else:
        with pytest.raises(CaptchaException) as error:
            await provider.verify(record, CaptchaAnswer(captcha_verify_param="opaque"), None)
        assert error.value.error_code == code


@pytest.mark.parametrize("code", [0, 1, 7, 8, 9, 15, 16, 21, 100])
async def test_tencent_request_and_result(cloud_settings, http_client, code):
    def reply(request):
        body = json.loads(request.content)
        assert body == {
            "CaptchaType": 9,
            "Ticket": "test-ticket",
            "Randstr": "test-rand",
            "UserIp": "2001:db8::1",
            "CaptchaAppId": 123456,
            "AppSecretKey": "test-app-secret",
        }
        assert request.headers["x-tc-version"] == "2019-07-22"
        assert request.headers["x-tc-action"] == "DescribeCaptchaResult"
        assert request.headers["authorization"].startswith("TC3-HMAC-SHA256 Credential=test-id/")
        return httpx.Response(
            200, json={"Response": {"CaptchaCode": code, "CaptchaMsg": "sensitive-message"}}
        )

    await mocked(http_client, reply)
    provider = TencentCaptchaProvider(cloud_settings.tencent, http_client)
    _, record = provider.create("login")
    assert await provider.verify(
        record, CaptchaAnswer(ticket="test-ticket", randstr="test-rand"), "2001:db8::1"
    ) is (code == 1)


@pytest.mark.parametrize(
    "response,expected",
    [
        ({"Response": {"CaptchaCode": True}}, Codes.PROVIDER_RESPONSE),
        ({"Response": {"CaptchaCode": "1"}}, Codes.PROVIDER_RESPONSE),
        ({"Response": {"CaptchaCode": 999}}, Codes.PROVIDER_RESPONSE),
        (
            {"Response": {"Error": {"Code": "InternalError", "Message": "secret"}}},
            Codes.PROVIDER_FAILURE,
        ),
        ({"CaptchaCode": 1}, Codes.PROVIDER_RESPONSE),
    ],
)
async def test_tencent_malformed_response(cloud_settings, http_client, response, expected):
    await mocked(http_client, lambda request: httpx.Response(200, json=response))
    provider = TencentCaptchaProvider(cloud_settings.tencent, http_client)
    _, record = provider.create("login")
    with pytest.raises(CaptchaException) as error:
        await provider.verify(record, CaptchaAnswer(ticket="t", randstr="r"), "127.0.0.1")
    assert error.value.error_code == expected


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("timeout", Codes.PROVIDER_TIMEOUT),
        ("budget", Codes.PROVIDER_TIMEOUT),
        ("network", Codes.PROVIDER_FAILURE),
        ("http", Codes.PROVIDER_FAILURE),
        ("json", Codes.PROVIDER_RESPONSE),
        ("size", Codes.PROVIDER_RESPONSE),
        ("encoding", Codes.PROVIDER_RESPONSE),
        ("array", Codes.PROVIDER_RESPONSE),
    ],
)
async def test_http_failures_and_limits(http_client, kind, expected):
    calls = []

    async def reply(request):
        calls.append(request)
        if kind == "timeout":
            raise httpx.ReadTimeout("private-ticket-secret", request=request)
        if kind == "budget":
            await asyncio.sleep(0.1)
        if kind == "network":
            raise httpx.ConnectError("private-key", request=request)
        if kind == "http":
            return httpx.Response(503, content=b"private-response")
        if kind == "json":
            return httpx.Response(200, content=b"{broken-private-secret")
        if kind == "size":
            return httpx.Response(200, content=b"x" * 32769)
        if kind == "encoding":
            return httpx.Response(200, headers={"content-encoding": "unknown"}, content=b"secret")
        return httpx.Response(200, json=[])

    if kind == "budget":
        http_client.settings = http_client.settings.model_copy(
            update={"cloud_timeout_seconds": 0.02}
        )
    await mocked(http_client, reply)
    with pytest.raises(CaptchaException) as error:
        await http_client.post("captcha.tencentcloudapi.com", {}, b"private-request")
    assert error.value.error_code == expected
    assert len(calls) == 1


async def test_cancellation_is_not_converted_to_success(http_client):
    async def reply(request):
        raise asyncio.CancelledError()

    await mocked(http_client, reply)
    with pytest.raises(asyncio.CancelledError):
        await http_client.post("captcha.tencentcloudapi.com", {}, b"")


@pytest.mark.parametrize("provider", ["aliyun", "tencent"])
async def test_selected_cloud_provider_issues_one_time_proof_and_closes(captcha_app, provider):
    app = await captcha_app(
        provider=provider,
        aliyun={
            "access_key_id": "private-id",
            "access_key_secret": "private-secret",
            "scene_id": "scene",
            "prefix": "prefix",
        },
        tencent={
            "app_id": 123456,
            "app_secret": "private-app-secret",
            "secret_id": "private-id",
            "secret_key": "private-secret",
        },
    )
    with app.state.application_context.execution():
        service = app.state.captcha
        transport = service._http
        response = (
            {"Success": True, "Result": {"VerifyResult": True}}
            if provider == "aliyun"
            else {"Response": {"CaptchaCode": 1}}
        )
        await mocked(transport, lambda request: httpx.Response(200, json=response))
        challenge = await service.create("login")
        assert "private-" not in challenge.model_dump_json()
        answer = (
            {"captcha_verify_param": "opaque-v3=="}
            if provider == "aliyun"
            else {"ticket": "ticket", "randstr": "rand"}
        )
        if provider == "tencent":
            with pytest.raises(CaptchaException) as error:
                await service.check(challenge.token, "login", answer)
            assert error.value.error_code == Codes.INVALID_INPUT
        proof = await service.check(challenge.token, "login", answer, client_ip="127.0.0.1")
        await service.consume(proof.verification, "login")
        await service.close()
        assert transport.client.is_closed
