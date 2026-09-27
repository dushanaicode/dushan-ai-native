from pydantic import BaseModel, ConfigDict, Field

from framework.starter_captcha.definitions.constants.captcha_image import CaptchaImage


class CaptchaPoint(BaseModel):
    """原图左上角为原点，单位为像素；缩放后的前端坐标必须先换算。"""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    x: float = Field(ge=0, lt=CaptchaImage.WIDTH, allow_inf_nan=False, repr=False)
    y: float = Field(ge=0, lt=CaptchaImage.HEIGHT, allow_inf_nan=False, repr=False)
