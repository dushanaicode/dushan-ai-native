from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class UserImportRespVO(BaseVO):
    """管理后台 - 用户导入 Response VO"""

    create_usernames: Annotated[list[str], Field(..., description="创建成功的用户名数组")]
    update_usernames: Annotated[list[str], Field(..., description="更新成功的用户名数组")]
    failure_usernames: Annotated[
        dict[str, str], Field(..., description="导入失败的用户集合，key 为用户名，value 为失败原因")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "createUsernames": ["user1", "user2"],
                    "updateUsernames": ["user3", "user4"],
                    "failureUsernames": {"user5": "邮箱格式不正确", "user6": "手机号已存在"},
                }
            ]
        }
    }
