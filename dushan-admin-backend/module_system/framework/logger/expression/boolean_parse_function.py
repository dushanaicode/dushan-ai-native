from framework.starter_di.decorators.components import service


@service
class BooleanParseFunction:
    NAME = "get_boolean"

    async def apply(self, value):
        if value is None:
            return ""
        if type(value) is not bool:
            raise ValueError("布尔差异字段必须使用 bool")
        return "是" if value else "否"
