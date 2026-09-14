from collections.abc import Collection


class PermissionPolicy:
    """只匹配服务端声明，不按 URL 或客户端字段推断授权。"""

    ALL = "*:*:*"

    @classmethod
    def all(cls, granted: Collection[str], required: Collection[str]) -> bool:
        return not required or cls.ALL in granted or set(required).issubset(granted)

    @classmethod
    def any(cls, granted: Collection[str], required: Collection[str]) -> bool:
        return bool(required) and (cls.ALL in granted or not set(required).isdisjoint(granted))

    @classmethod
    def intersect(cls, left: Collection[str], right: Collection[str]) -> frozenset[str]:
        if cls.ALL in left:
            return frozenset(right)
        if cls.ALL in right:
            return frozenset(left)
        return frozenset(left) & frozenset(right)
