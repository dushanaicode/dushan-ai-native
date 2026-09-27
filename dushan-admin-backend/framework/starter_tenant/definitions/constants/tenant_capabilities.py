class TenantCapabilities:
    """部署能力标识；direct_membership始终具备，不属于自定义可选能力。

    SUPPORT_SESSION对应RoutePolicy的同名门控；Web保持该协议字符串以避免反向依赖Tenant。
    """

    ACCOUNT_SELECTION = "account_selection"
    GROUP_MANAGED_ACCESS = "group_managed_access"
    GROUP_DATA_SHARING = "group_data_sharing"
    PLATFORM_CONTROL_PLANE = "platform_control_plane"
    MANUAL_PROVISIONING = "manual_provisioning"
    SELF_SERVICE_PROVISIONING = "self_service_provisioning"
    SUPPORT_SESSION = "support_session"
    DIRECT_MEMBERSHIP = "direct_membership"
    CUSTOM = frozenset(
        {
            ACCOUNT_SELECTION,
            GROUP_MANAGED_ACCESS,
            GROUP_DATA_SHARING,
            PLATFORM_CONTROL_PLANE,
            MANUAL_PROVISIONING,
            SELF_SERVICE_PROVISIONING,
            SUPPORT_SESSION,
        }
    )
