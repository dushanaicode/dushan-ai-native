from framework.common.enums import BaseEnum


class AnnouncementCategoryEnum(BaseEnum):
    SYSTEM_MAINTENANCE = (1, "系统维护通知")
    FEATURE_RELEASE = (2, "新功能发布")
    POLICY_CHANGE = (3, "重要政策变更")
