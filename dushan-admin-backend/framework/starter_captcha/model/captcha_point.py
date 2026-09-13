from pydantic import BaseModel, ConfigDict, Field


class CaptchaPoint(BaseModel):
    """原图左上角为原点，单位为像素；缩放后的前端坐标必须先换算。"""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    x: float = Field(ge=0, lt=320, allow_inf_nan=False, repr=False)
    y: float = Field(ge=0, lt=160, allow_inf_nan=False, repr=False)
