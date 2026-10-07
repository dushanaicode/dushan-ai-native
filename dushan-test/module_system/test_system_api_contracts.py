from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.common.page import PageResult
from framework.common.schemas.request import IdReqVO
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.api.logger.dto.operate_log_resp_dto import OperateLogRespDTO
from module_system.api.logger.operate_log_api_impl import OperateLogApiImpl
from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO
from module_system.controller.admin.dict.dict_data_controller import DictDataController
from module_system.controller.admin.dict.vo.data.dict_data_resp_vo import DictDataRespVO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO


class TestSystemApiContracts:
    async def test_operate_log_page_converts_items_and_preserves_total(self):
        """操作日志分页把服务对象转成响应 DTO，并保留总数。"""
        request = OperateLogPageReqDTO(page=2, page_size=1)
        service = SimpleNamespace(
            get_operate_log_page_dto=AsyncMock(
                return_value=PageResult(items=[SimpleNamespace(id=7, action="更新字典")], total=13)
            )
        )
        api = OperateLogApiImpl()
        api.operate_log_service = service

        result = await api.get_operate_log_page(request)

        service.get_operate_log_page_dto.assert_awaited_once_with(request)
        assert result.total == 13
        assert len(result.items) == 1
        assert isinstance(result.items[0], OperateLogRespDTO)
        assert result.items[0].id == 7
        assert result.items[0].action == "更新字典"

    @pytest.mark.parametrize("exists", [False, True])
    async def test_dict_detail_returns_success_for_nullable_service_result(self, exists):
        """字典详情不存在时成功返回 null，存在时保持响应转换。"""
        record = (
            DictDataDO(
                id=7,
                sort=1,
                label="开启",
                value="enabled",
                dict_type="test_status",
                status=1,
                create_time=datetime(2026, 10, 4),
            )
            if exists
            else None
        )
        service = SimpleNamespace(get_dict_data=AsyncMock(return_value=record))

        result = await DictDataController.get_dict_data(IdReqVO(id="7"), service)

        service.get_dict_data.assert_awaited_once_with(7)
        assert result.code == 0
        if exists:
            assert isinstance(result.data, DictDataRespVO)
            assert result.data.label == "开启"
            assert result.data.dict_type == "test_status"
        else:
            assert result.model_dump(mode="json")["data"] is None

    def test_admin_user_schema_example_satisfies_dto_contract(self):
        """用户 DTO 示例采用模型接受的字段名并保留部门和岗位。"""
        example = AdminUserRespDTO.model_json_schema()["examples"][0]

        user = AdminUserRespDTO.model_validate(example)

        assert user.dept_id == 100
        assert user.post_ids == {1, 2}
