from __future__ import annotations

from datetime import datetime

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class SocialWxaOrderNotifyConfirmReceiveReqDTO(BaseDTO):
    """
    小程序订单确认收货通知 DTO

    See: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/shopping-order/normal-shopping-detail/uploadShoppingInfo.html
    """

    transaction_id: str = Field(..., description="原支付交易对应的微信订单号")
    received_time: datetime = Field(..., description="快递签收时间")
