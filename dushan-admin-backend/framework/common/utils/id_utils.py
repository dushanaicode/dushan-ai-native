import secrets
import string
from uuid import uuid4


class IdUtils:
    """生成随机标识和 UUID；是否采用某种数据库主键由业务另行决定。"""

    @staticmethod
    def nano_id(size: int = 21) -> str:
        """使用密码学随机源生成字母数字标识；长度由调用处选择。"""
        if type(size) is not int or size <= 0:
            raise ValueError("随机标识长度必须是正整数")
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(size))

    @staticmethod
    def simple_uuid() -> str:
        """生成无连字符的 UUID4，不包含本机地址信息。"""
        return uuid4().hex
