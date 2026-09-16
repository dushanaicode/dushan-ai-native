from typing import Protocol


class SocketProjection(Protocol):
    async def project(self, payload, context):
        """在接收者的真实 Security/Tenant/Data Permission 执行中投影；None 表示不发送。

        返回声明事件模型。需要行级权限的消息应传资源定位并在此重新查询，不能把
        高权限查询结果不加区分地广播给低权限连接。
        """
        ...
