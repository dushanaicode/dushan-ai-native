from typing import Protocol


class IpLocationProvider(Protocol):
    """DI 多实现扩展入口；None 仅表示正常未命中，故障必须抛出。

    query 在 IP 服务持有的共享任务内执行，不继承请求 ContextVar。
    Provider 必须通过构造注入取得应用依赖，不读取请求身份或依赖 ambient get_bean。
    取消时完成自身响应流等资源清理；服务关闭会等待该任务的实际终态。
    """

    name: str
    online: bool

    async def query(self, ip: str, remaining_seconds: float) -> str | None: ...
