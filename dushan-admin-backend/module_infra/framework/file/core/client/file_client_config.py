from __future__ import annotations

from pydantic import ConfigDict

from framework.common.schemas import BaseVO


class FileClientConfig(BaseVO):
    """文件客户端配置基类的 Pydantic 版本"""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
