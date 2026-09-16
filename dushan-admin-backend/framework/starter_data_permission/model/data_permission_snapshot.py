from pydantic import BaseModel, ConfigDict

from framework.starter_data_permission.model.data_grant import DataGrant


class DataPermissionSnapshot(BaseModel):
    """缓存同时校验完整身份、授权版本和规则版本；不接受客户端构造。"""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)

    binding: str
    revision: str
    grant: DataGrant

    def __repr_args__(self):
        return iter(())
