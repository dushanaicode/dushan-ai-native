from typing import Any, Self

from pydantic import Field, PrivateAttr, field_validator

from framework.common.page.constants.page_size_constants import PageSizeConstants
from framework.common.schemas.base_request_vo import BaseRequestVO


class PageQuery(BaseRequestVO):
    """描述一次分页请求，pageSize 省略时使用当前应用配置。

    对外使用page/pageSize；全量读取是服务端私有状态，不能由JSON字段开启。
    服务端可调用 enable_fetch_all(max_rows=...)，仍需通过分页器的平台开关和上限检查。
    """

    page: int = Field(default=PageSizeConstants.PAGE_NO_DEFAULT, ge=1)
    page_size: int | None = Field(default=None, ge=1, description="省略时采用应用默认页大小")
    _fetch_all: bool = PrivateAttr(default=False)
    _fetch_all_max_rows: int | None = PrivateAttr(default=None)

    @field_validator("page", "page_size", mode="before")
    @classmethod
    def reject_boolean_page_values(cls, value: Any) -> Any:
        """页码和条数不能用布尔值代替。"""
        if isinstance(value, bool):
            raise ValueError("页码和条数不能是布尔值")
        return value

    @property
    def fetch_all(self) -> bool:
        """返回是否由服务端明确开启全量读取。"""
        return self._fetch_all

    @property
    def fetch_all_max_rows(self) -> int | None:
        """返回接口自行收紧的全量上限，None 表示采用平台上限。"""
        return self._fetch_all_max_rows

    def enable_fetch_all(self, *, max_rows: int | None = None) -> Self:
        """声明受控全量读取，拒绝 NaN、无穷值和非整数上限。"""
        if max_rows is not None and (type(max_rows) is not int or max_rows < 1):
            raise ValueError("max_rows 必须是正整数")
        self._fetch_all = True
        self._fetch_all_max_rows = max_rows
        return self
