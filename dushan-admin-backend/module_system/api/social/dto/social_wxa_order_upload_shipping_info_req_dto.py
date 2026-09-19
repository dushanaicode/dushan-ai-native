from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from framework.common.schemas import BaseDTO


class SocialWxaOrderUploadShippingInfoReqDTO(BaseDTO):
    """
    小程序订单上传购物详情

    See: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/shopping-order/normal-shopping-detail/uploadShoppingInfo.html
    """

    LOGISTICS_TYPE_EXPRESS: ClassVar[int] = 1
    LOGISTICS_TYPE_VIRTUAL: ClassVar[int] = 3
    LOGISTICS_TYPE_PICK_UP: ClassVar[int] = 4
    openid: str = Field(..., description="支付者，支付者信息(openid)")
    transaction_id: str = Field(..., description="原支付交易对应的微信订单号")
    logistics_type: int = Field(..., description="物流模式")
    logistics_no: str | None = Field(None, description="物流发货单号")
    express_company: str | None = Field(None, description="物流公司编号")
    item_desc: str = Field(..., description="商品信息")
    receiver_contact: str | None = Field(None, description="收件人手机号")
