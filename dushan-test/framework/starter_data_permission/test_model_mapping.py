import pytest

from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)


@pytest.mark.parametrize(
    ("permission_case", "rule", "expected"),
    [
        ({"model_scope": "membership"}, DataScope.SELF, [1]),
        ({"model_scope": "membership"}, DataScope.DEPT_ONLY, [1, 2]),
        ({"model_scope": "membership"}, DataScope.DEPT_AND_CHILD, [1, 2, 3, 4]),
        ({"model_scope": "department"}, DataScope.SELF, []),
        ({"model_scope": "department"}, DataScope.DEPT_ONLY, [1, 2]),
        ({"model_scope": "department"}, DataScope.DEPT_AND_CHILD, [1, 2, 3, 4]),
    ],
    indirect=["permission_case"],
)
async def test_membership_and_department_model_modes(permission_case, rule, expected):
    case = permission_case
    await case.set_rules(rule)
    async with case.enter():
        assert await case.ids() == expected


@pytest.mark.parametrize("permission_case", [{"renamed": True}], indirect=True)
async def test_renamed_orm_property_uses_controlled_column(permission_case):
    case = permission_case
    async with case.enter():
        assert await case.ids() == [1]
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                item = await session.get(case.Item, 1)
                item.owner = "m3"
                await session.flush()
