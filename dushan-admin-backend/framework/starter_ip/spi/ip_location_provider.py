from typing import Protocol


class IpLocationProvider(Protocol):
    """DI 多实现扩展入口；None 仅表示正常未命中，故障必须抛出。

    query 在 IP 服务持有的共享任务内执行，不继承请求 ContextVar。
    Provider 必须通过构造注入取得应用依赖，不读取请求身份或依赖 ApplicationContext.lookup。
    取消时完成自身响应流等资源清理；服务关闭会等待该任务的实际终态。
    查询故障使用IpException(QUERY_FAILED)，context提供provider名称与安全reason分类；
    地址族未启用使用FAMILY_NOT_ENABLED并提供family，不以空结果掩盖故障。
    """

    name: str
    online: bool

    async def query(self, ip: str, remaining_seconds: float) -> str | None: ...
