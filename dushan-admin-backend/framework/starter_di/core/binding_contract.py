from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class BindingContract:
    """在注册边界校验类型，非 runtime Protocol 要求显式声明实现关系。"""

    @staticmethod
    def validate_implementation(interface: type, implementation: type) -> None:
        if getattr(interface, "_is_protocol", False):
            matches = interface in implementation.__mro__
        else:
            matches = issubclass(implementation, interface)
        if not matches:
            raise DiException(
                error_code=DiErrorCodes.INVALID_DEFINITION,
                msg=f"实现类未声明接口契约：{implementation.__qualname__} -> {interface.__qualname__}",
            )

    @staticmethod
    def validate_instance(interface: type, instance: object) -> None:
        if not isinstance(interface, type):
            raise DiException(
                error_code=DiErrorCodes.INVALID_DEFINITION, msg="实例绑定键必须是明确类型"
            )
        if getattr(interface, "_is_protocol", False) and not getattr(
            interface, "_is_runtime_protocol", False
        ):
            matches = interface in type(instance).__mro__
        else:
            matches = isinstance(instance, interface)
        if not matches:
            raise DiException(
                error_code=DiErrorCodes.INVALID_DEFINITION,
                msg=f"外部实例不符合绑定类型：{interface.__module__}.{interface.__qualname__}",
            )
