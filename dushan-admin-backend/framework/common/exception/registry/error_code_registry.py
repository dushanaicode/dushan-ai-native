from loguru import logger

from framework.common.exception.core.error_code import ErrorCode

__all__ = ["ErrorCodeRegistry"]


class ErrorCodeRegistry:
    """收集错误码常量，检查编号冲突并提供查询入口。

    启动时将带 @error_code 标记的常量类传入 register_all，随后通过
    get_by_code 查询定义，或通过 get_all_detail 获取生成文档所需的来源。
    注册状态在进程内共享；相同编号会抛出配置异常，调用方应终止初始化。
    """

    # 错误码映射：(类名, 属性名, 错误码对象)
    _registry: dict[int, tuple[str, str, ErrorCode]] = {}
    _initialized: bool = False

    @classmethod
    def register_class(cls, source_class: type) -> int:
        """注册常量类中的公开错误码；遇到冲突时抛出配置异常。"""
        count = 0
        class_name = source_class.__name__

        for name in dir(source_class):
            if name.startswith("_"):
                continue
            value = getattr(source_class, name, None)
            if not isinstance(value, ErrorCode):
                continue

            cls._validate_error_code(class_name, name, value)

            existing = cls._registry.get(value.code)
            if existing is not None:
                # 延迟导入避免循环依赖
                from framework.common.exception.exceptions.configuration_exception import (
                    ConfigurationException,
                )

                raise ConfigurationException(
                    msg=(
                        f"错误码冲突: {value.code} 被 {existing[0]}.{existing[1]} 和 {class_name}.{name} 同时使用"
                    )
                )

            cls._registry[value.code] = (class_name, name, value)
            count += 1

        if count > 0:
            cls._initialized = True
        return count

    @staticmethod
    def _validate_error_code(class_name: str, attr_name: str, error_code: ErrorCode) -> None:
        """校验错误码定义必须包含描述和国际化消息 key。"""
        if error_code.description and error_code.message_key:
            return

        from framework.common.exception.exceptions.configuration_exception import (
            ConfigurationException,
        )

        raise ConfigurationException(
            msg=f"错误码定义不完整: {class_name}.{attr_name} 必须提供 description 和 message_key"
        )

    @classmethod
    def register_all(cls, classes: list) -> None:
        """清空旧状态并批量注册错误码常量类。"""
        cls.reset()
        total = 0
        for klass in classes:
            total += cls.register_class(klass)
        cls._initialized = True
        logger.info("错误码注册完成，共 {} 个错误码，来自 {} 个常量类", total, len(classes))

    @classmethod
    def get_by_code(cls, code: int) -> ErrorCode | None:
        """按编号查找错误码定义，未注册时返回 None。"""
        entry = cls._registry.get(code)
        return entry[2] if entry else None

    @classmethod
    def get_all(cls) -> dict[int, ErrorCode]:
        """返回已注册错误码的映射副本。"""
        return {code: entry[2] for code, entry in cls._registry.items()}

    @classmethod
    def get_all_detail(cls) -> dict[int, tuple[str, str, ErrorCode]]:
        """返回包含常量类名、属性名和错误码的映射副本。"""
        return dict(cls._registry)

    @classmethod
    def is_initialized(cls) -> bool:
        """返回注册中心是否已初始化。"""
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        """清空错误码与初始化状态。"""
        cls._registry.clear()
        cls._initialized = False
