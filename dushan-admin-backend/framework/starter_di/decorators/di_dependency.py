from starlette.requests import HTTPConnection

from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class DiDependency:
    """FastAPI Depends 的应用级入口：Depends(DiDependency(UserService))。"""

    def __init__(self, component: type) -> None:
        self.component = component

    def __call__(self, connection: HTTPConnection) -> object:
        try:
            application = connection.app.state.application_context
        except AttributeError as error:
            raise DiException(
                error_code=DiErrorCodes.NOT_READY, msg="应用尚未发布 DI 容器", cause=error
            ) from error
        if application is None:
            raise DiException(error_code=DiErrorCodes.NOT_READY, msg="当前应用未启用 DI")
        return application.container.get(self.component)
