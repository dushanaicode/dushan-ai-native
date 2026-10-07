from types import SimpleNamespace

import pytest

from framework.starter_security.bizlog.diff_renderer import DiffRenderer
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO


class TestUserDiffMasking:
    async def test_changed_contact_details_are_masked(self):
        """联系方式发生变更时保留差异记录，但不输出任一原始值。"""
        before = UserSaveReqVO(
            id="10",
            username="fixture",
            nickname="用户",
            email="a@old.cn",
            mobile="13800138000",
        )
        after = UserSaveReqVO(
            id="10",
            username="fixture",
            nickname="用户",
            email="b@new.cn",
            mobile="13900139000",
        )
        renderer = DiffRenderer(SimpleNamespace(bizlog_max_diff_items=20, bizlog_max_length=2000))

        rendered = await renderer.render(before, after)

        assert rendered == ("用户邮箱: a******n → b******n；手机号码已变更")
        for value in (before.email, after.email, before.mobile, after.mobile):
            assert value not in rendered
        assert await renderer.render(before, before) == ""

    @pytest.mark.parametrize(
        ("field", "value", "masked", "label"),
        [
            ("email", "a@old.cn", "a******n", "用户邮箱"),
            ("mobile", "13800138000", "1*********0", "手机号码"),
        ],
    )
    @pytest.mark.parametrize("clearing", [False, True])
    async def test_contact_addition_and_removal_are_masked(
        self, field, value, masked, label, clearing
    ):
        """新增或清空联系方式均记录差异，并只展示脱敏后的非空值。"""
        empty = UserSaveReqVO(id="10", username="fixture", nickname="用户")
        populated = UserSaveReqVO(id="10", username="fixture", nickname="用户", **{field: value})
        renderer = DiffRenderer(SimpleNamespace(bizlog_max_diff_items=20, bizlog_max_length=2000))
        before, after = (populated, empty) if clearing else (empty, populated)

        rendered = await renderer.render(before, after)

        expected = f"{masked} → None" if clearing else f"None → {masked}"
        assert rendered == f"{label}: {expected}"
        assert value not in rendered
