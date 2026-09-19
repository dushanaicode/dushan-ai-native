from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class DiErrorCodes:
    """容器、绑定和状态的稳定失败编号，不恢复全局单例相关错误。"""

    ERROR = ErrorCode(code=1_013_000, description="依赖注入失败", message_key="di.error")
    NOT_READY = ErrorCode(
        code=1_013_002, description="依赖容器尚未就绪或已关闭", message_key="di.not_ready"
    )
    DUPLICATE_BINDING = ErrorCode(
        code=1_013_021, description="依赖接口绑定冲突", message_key="di.duplicate_binding"
    )
    CIRCULAR_DEPENDENCY = ErrorCode(
        code=1_013_022, description="依赖关系存在循环", message_key="di.circular_dependency"
    )
    MISSING_BINDING = ErrorCode(
        code=1_013_023, description="缺少显式依赖绑定", message_key="di.missing_binding"
    )
    INVALID_PROVIDER = ErrorCode(
        code=1_013_024,
        description="组件未实现声明的 Provider 接口",
        message_key="di.invalid_provider",
    )
    INVALID_DEFINITION = ErrorCode(
        code=1_013_025, description="依赖组件声明无效", message_key="di.invalid_definition"
    )
    STATE_NOT_FOUND = ErrorCode(
        code=1_013_033, description="必需运行状态未注册", message_key="di.state_not_found"
    )
    INVALID_STATE = ErrorCode(
        code=1_013_035, description="运行状态值类型不匹配", message_key="di.invalid_state"
    )
    INVALID_LIFECYCLE = ErrorCode(
        code=1_013_056,
        description="组件生命周期缺少有效释放边界",
        message_key="di.invalid_lifecycle",
    )
    CONTEXT_MISSING = ErrorCode(
        code=1_013_070, description="当前执行未绑定应用上下文", message_key="di.context_missing"
    )
    CONTEXT_EXPIRED = ErrorCode(
        code=1_013_071,
        description="执行上下文已过期",
        message_key="di.context_expired",
    )
    CONTEXT_MISMATCH = ErrorCode(
        code=1_013_072, description="服务与当前执行属于不同应用", message_key="di.context_mismatch"
    )
    LOOKUP_DISABLED = ErrorCode(
        code=1_013_073, description="应用已关闭外部服务获取入口", message_key="di.lookup_disabled"
    )
    DRAIN_TIMEOUT = ErrorCode(
        code=1_013_074, description="业务执行排空超过协作期限", message_key="di.drain_timeout"
    )
    TASK_FAILED = ErrorCode(
        code=1_013_075, description="应用后台任务执行失败", message_key="di.task_failed"
    )
