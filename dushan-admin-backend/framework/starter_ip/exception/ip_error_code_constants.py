from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class IpErrorCodeConstants:
    IP_ERROR = ErrorCode(code=1_003_000, description="IP 模块异常", message_key="ip.error")
    AREA_DATA_LOAD_ERROR = ErrorCode(
        code=1_003_001, description="地区数据加载失败", message_key="ip.area_data_load_error"
    )
    NOT_INITIALIZED = ErrorCode(
        code=1_003_002, description="IP 资源尚未初始化或已经关闭", message_key="ip.not_initialized"
    )
    XDB_LOAD_ERROR = ErrorCode(
        code=1_003_003, description="ip2region 数据校验失败", message_key="ip.xdb_load_error"
    )
    FAMILY_NOT_ENABLED = ErrorCode(
        code=1_003_004, description="本地 IP 地址族未启用", message_key="ip.family_not_enabled"
    )
    QUERY_FAILED = ErrorCode(
        code=1_003_011, description="IP 归属地查询失败", message_key="ip.query_failed"
    )
