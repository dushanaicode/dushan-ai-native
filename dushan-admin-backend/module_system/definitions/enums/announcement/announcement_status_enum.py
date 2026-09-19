from framework.common.enums import BaseEnum


class AnnouncementStatusEnum(BaseEnum):
    DRAFT = (0, "草稿")
    WAIT_PUBLISH = (1, "待发布")
    PUBLISHED = (2, "已发布")
    EXPIRED = (3, "已过期")
