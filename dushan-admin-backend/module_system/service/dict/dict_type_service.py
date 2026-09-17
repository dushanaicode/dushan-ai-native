from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO
from module_system.controller.admin.dict.vo.type.type_save_req_vo import DictTypeSaveReqVO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO


@runtime_checkable
class DictTypeService(Protocol):
    async def get_dict_type_page(
        self, page_req_vo: DictTypePageReqVO
    ) -> PageResult[DictTypeDO]: ...

    async def get_dict_type_by_id(self, id: int) -> DictTypeDO | None: ...

    async def get_dict_type_by_type(self, type_str: str) -> DictTypeDO | None: ...

    async def create_dict_type(self, create_req_vo: DictTypeSaveReqVO) -> int: ...

    async def update_dict_type(self, update_req_vo: DictTypeSaveReqVO) -> None: ...

    async def update_status(self, dict_type_id: int, status: int) -> None: ...

    async def delete_dict_type(self, id: int) -> None: ...

    async def delete_dict_type_batch(self, ids: list[int]) -> int: ...

    async def get_dict_type_list(self) -> list[DictTypeDO]: ...
