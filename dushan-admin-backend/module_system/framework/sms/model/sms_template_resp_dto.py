from framework.common.schemas import BaseDTO


class SmsTemplateRespDTO(BaseDTO):
    """短信模板 Response DTO"""

    id: str | None = None
    content: str | None = None
    audit_status: int | None = None
    audit_reason: str | None = None
