import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from framework.starter_auth.exception.auth_exception import AuthException

from .support import ACCESS, FLOW, REFRESH, body, client_config, provider_case, settings


@pytest.fixture(scope="module")
def signing_keys():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048), rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )


def config(source, keys):
    private, upstream = keys
    secret = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public = (
        upstream.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    options = (
        {
            "app_cert_sn": "a" * 32,
            "alipay_root_cert_sn": "b" * 32 + "_" + "c" * 32,
            "alipay_cert_sn": "d" * 32,
        }
        if source == "ALIPAY_CERT"
        else {}
    )
    return client_config(
        source,
        client_secret=secret,
        credentials={"alipay_public_key": public},
        options={**options, "subject_type": "open_id" if source == "ALIPAY_CERT" else "user_id"},
    )


def response(keys, method, data, *, certificate=False):
    # 含空格、嵌套对象和括号字符串，验证的是原始 JSON 字节而非重新 dumps 后的内容。
    data = {**data, "nested": {"text": 'quoted" } text'}}
    payload = json.dumps(data, ensure_ascii=False, indent=1)
    signature = base64.b64encode(
        keys[1].sign(payload.encode(), padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    extra = ', "alipay_cert_sn":"' + "d" * 32 + '"' if certificate else ""
    return (
        '{ "'
        + method.replace(".", "_")
        + '_response" : '
        + payload
        + ', "sign":"'
        + signature
        + '"'
        + extra
        + " }"
    )


@pytest.mark.parametrize("source", ["ALIPAY", "ALIPAY_CERT"])
async def test_alipay_signed_token_profile_refresh(source, signing_keys):
    cfg = config(source, signing_keys)
    token = {
        "access_token": ACCESS,
        "refresh_token": REFRESH,
        "expires_in": "600",
        "user_id": "123",
    }
    profile = {
        "code": "10000",
        "user_id": "123",
        "open_id": "456",
        "nick_name": "用户",
        "province": "浙江",
        "city": "杭州",
    }
    replies = [
        response(signing_keys, method, data, certificate=source == "ALIPAY_CERT")
        for method, data in [
            ("alipay.system.oauth.token", token),
            ("alipay.user.info.share", profile),
            ("alipay.system.oauth.token", token),
        ]
    ]
    provider, transport, http = await provider_case(source, replies, cfg)
    try:
        provider.validate_client(cfg, settings())
        tokens = await provider.exchange("code+with/symbols", FLOW)
        user = await provider.userinfo(tokens)
        refreshed = await provider.refresh(tokens)
        assert user.subject == ("456" if source == "ALIPAY_CERT" else "123")
        assert user.nickname == "用户" and user.location == "浙江 杭州"
        assert refreshed.refresh_token.get_secret_value() == REFRESH
        for request in transport.requests:
            params = body(request)
            signature = base64.b64decode(params.pop("sign"), validate=True)
            canonical = "&".join(k + "=" + v for k, v in sorted(params.items()))
            signing_keys[0].public_key().verify(
                signature, canonical.encode(), padding.PKCS1v15(), hashes.SHA256()
            )
            assert (
                params["sign_type"] == "RSA2" and request.method == "POST" and not request.url.query
            )
            if source == "ALIPAY_CERT":
                assert params["app_cert_sn"] == "a" * 32
                assert params["alipay_root_cert_sn"] == "b" * 32 + "_" + "c" * 32
        assert body(transport.requests[0])["code"] == "code+with/symbols"
        assert body(transport.requests[-1])["grant_type"] == "refresh_token"
        assert not transport.responses
    finally:
        await http.close()


@pytest.mark.parametrize(
    "attack", ["signature", "missing_signature", "duplicate", "certificate", "business_error"]
)
async def test_alipay_bad_signed_response_rejected(attack, signing_keys):
    raw = response(
        signing_keys,
        "alipay.system.oauth.token",
        {"access_token": ACCESS, "expires_in": 600},
        certificate=True,
    )
    if attack == "signature":
        raw = raw.replace(ACCESS, "tampered")
    if attack == "missing_signature":
        raw = raw.replace('"sign":', '"ignored":')
    if attack == "duplicate":
        raw = raw.replace('"sign":', '"sign":"first","sign":')
    if attack == "certificate":
        raw = raw.replace("d" * 32, "e" * 32)
    if attack == "business_error":
        raw = response(
            signing_keys,
            "alipay.system.oauth.token",
            {"code": "40004", "sub_msg": ACCESS},
            certificate=True,
        )
    provider, transport, http = await provider_case(
        "ALIPAY_CERT", [raw], config("ALIPAY_CERT", signing_keys)
    )
    try:
        with pytest.raises(AuthException) as failure:
            await provider.exchange("code", FLOW)
        assert ACCESS not in str(failure.value)
        assert len(transport.requests) == 1
    finally:
        await http.close()


@pytest.mark.parametrize("source", ["ALIPAY", "ALIPAY_CERT"])
@pytest.mark.parametrize("subject_type", ["user_id", "open_id"])
async def test_identity_type_is_application_setting_not_signing_mode(
    source, subject_type, signing_keys
):
    original = config(source, signing_keys)
    cfg = original.model_copy(
        update={"options": {**original.options, "subject_type": subject_type}}
    )
    raw = response(
        signing_keys,
        "alipay.user.info.share",
        {"code": "10000", subject_type: "raw-id"},
        certificate=source == "ALIPAY_CERT",
    )
    provider, transport, http = await provider_case(source, [raw], cfg)
    try:
        provider.validate_client(cfg, settings())
        identity = await provider.userinfo(provider.tokens(access_token=ACCESS))
        assert identity.subject == "raw-id" and identity.subject_type == subject_type
        assert identity.client_id == cfg.client_id
    finally:
        await http.close()


def test_alipay_identity_type_is_required(signing_keys):
    from framework.starter_auth.provider.alipay_provider import AlipayProvider

    cfg = config("ALIPAY", signing_keys).model_copy(update={"options": {}})
    with pytest.raises(AuthException):
        AlipayProvider.validate_client(cfg, settings())
