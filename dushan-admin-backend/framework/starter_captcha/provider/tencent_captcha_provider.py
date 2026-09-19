import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

from framework.starter_captcha.config.tencent_captcha_settings import TencentCaptchaSettings
from framework.starter_captcha.core.captcha_provider import CaptchaProvider
from framework.starter_captcha.definitions.constants.captcha_error_codes import (
    CaptchaErrorCodes as Codes,
)
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.model.captcha_record import CaptchaRecord
from framework.starter_captcha.provider.captcha_http_client import CaptchaHttpClient


class TencentCaptchaProvider(CaptchaProvider):
    """DescribeCaptchaResult 2019-07-22，普通验证码模式仅整数 1 表示通过。"""

    ENDPOINT = "captcha.tencentcloudapi.com"

    def __init__(self, settings: TencentCaptchaSettings, http: CaptchaHttpClient) -> None:
        self.settings = settings
        self.http = http

    def create(self, purpose: str) -> tuple[dict, CaptchaRecord]:
        return {"app_id": self.settings.app_id}, CaptchaRecord(
            provider="tencent", purpose=purpose, points=[]
        )

    def signed_request(
        self, answer: CaptchaAnswer, client_ip: str, timestamp: int
    ) -> tuple[dict[str, str], bytes]:
        body = json.dumps(
            {
                "CaptchaType": 9,
                "Ticket": answer.ticket,
                "Randstr": answer.randstr,
                "UserIp": client_ip,
                "CaptchaAppId": self.settings.app_id,
                "AppSecretKey": self.settings.app_secret.get_secret_value(),
            },
            separators=(",", ":"),
        ).encode()
        date = datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d")
        canonical = f"POST\n/\n\ncontent-type:application/json\nhost:{self.ENDPOINT}\n\ncontent-type;host\n{hashlib.sha256(body).hexdigest()}"
        scope = f"{date}/captcha/tc3_request"
        to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
        key = ("TC3" + self.settings.secret_key.get_secret_value()).encode()
        for value in (date, "captcha", "tc3_request"):
            key = hmac.new(key, value.encode(), hashlib.sha256).digest()
        signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
        return {
            "host": self.ENDPOINT,
            "content-type": "application/json",
            "x-tc-action": "DescribeCaptchaResult",
            "x-tc-version": "2019-07-22",
            "x-tc-timestamp": str(timestamp),
            "authorization": f"TC3-HMAC-SHA256 Credential={self.settings.secret_id.get_secret_value()}/{scope}, SignedHeaders=content-type;host, Signature={signature}",
        }, body

    async def verify(
        self, record: CaptchaRecord, answer: CaptchaAnswer, client_ip: str | None
    ) -> bool:
        headers, body = self.signed_request(answer, client_ip, int(time.time()))
        envelope = await self.http.post(self.ENDPOINT, headers, body)
        response = envelope.get("Response")
        if not isinstance(response, dict):
            raise CaptchaException(Codes.PROVIDER_RESPONSE)
        if "Error" in response:
            raise CaptchaException(Codes.PROVIDER_FAILURE)
        code = response.get("CaptchaCode")
        if type(code) is not int or code not in (0, 1, 7, 8, 9, 15, 16, 21, 100):
            raise CaptchaException(Codes.PROVIDER_RESPONSE)
        return code == 1
