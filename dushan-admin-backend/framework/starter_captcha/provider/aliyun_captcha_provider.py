import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode

from framework.starter_captcha.config.aliyun_captcha_settings import AliyunCaptchaSettings
from framework.starter_captcha.core.captcha_provider import CaptchaProvider
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.model.captcha_record import CaptchaRecord
from framework.starter_captcha.provider.captcha_http_client import CaptchaHttpClient


class AliyunCaptchaProvider(CaptchaProvider):
    """VerifyIntelligentCaptcha 2023-03-05，使用官方 ACS3 签名和 formData 协议。"""

    def __init__(self, settings: AliyunCaptchaSettings, http: CaptchaHttpClient) -> None:
        self.settings = settings
        self.http = http

    def create(self, purpose: str) -> tuple[dict, CaptchaRecord]:
        return {
            "scene_id": self.settings.scene_id,
            "prefix": self.settings.prefix,
            "region": self.settings.region,
            "language": self.settings.language,
        }, CaptchaRecord(provider="aliyun", purpose=purpose, points=[])

    def signed_request(self, parameter: str, date: str, nonce: str) -> tuple[dict[str, str], bytes]:
        body = urlencode(
            {"CaptchaVerifyParam": parameter, "SceneId": self.settings.scene_id}
        ).encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        headers = {
            "host": self.settings.endpoint,
            "x-acs-action": "VerifyIntelligentCaptcha",
            "x-acs-version": "2023-03-05",
            "x-acs-date": date,
            "x-acs-signature-nonce": nonce,
            "x-acs-content-sha256": digest,
        }
        names = ";".join(sorted(headers))
        canonical = (
            "POST\n/\n\n"
            + "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
            + f"\n{names}\n{digest}"
        )
        to_sign = "ACS3-HMAC-SHA256\n" + hashlib.sha256(canonical.encode()).hexdigest()
        signature = hmac.new(
            self.settings.access_key_secret.get_secret_value().encode(),
            to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["authorization"] = (
            f"ACS3-HMAC-SHA256 Credential={self.settings.access_key_id.get_secret_value()},SignedHeaders={names},Signature={signature}"
        )
        headers["content-type"] = "application/x-www-form-urlencoded"
        return headers, body

    async def verify(
        self, record: CaptchaRecord, answer: CaptchaAnswer, client_ip: str | None
    ) -> bool:
        headers, body = self.signed_request(
            answer.captcha_verify_param,
            datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            secrets.token_hex(16),
        )
        response = await self.http.post(self.settings.endpoint, headers, body)
        if type(response.get("Success")) is not bool:
            raise CaptchaException(Codes.PROVIDER_RESPONSE)
        if response["Success"] is False:
            raise CaptchaException(Codes.PROVIDER_FAILURE)
        result = response.get("Result")
        if not isinstance(result, dict) or type(result.get("VerifyResult")) is not bool:
            raise CaptchaException(Codes.PROVIDER_RESPONSE)
        return result["VerifyResult"]
