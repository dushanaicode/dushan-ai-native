from framework.common.enums import BaseEnum
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum


class FileUploadUsageEnum(BaseEnum):
    AVATAR = ("avatar", "头像")
    LOGO = ("logo", "Logo")
    FORM_IMAGE = ("form-image", "表单图片")
    FORM_FILE = ("form-file", "表单附件")

    @property
    def visibility(self) -> FileVisibilityEnum:
        if self in (self.AVATAR, self.LOGO):
            return FileVisibilityEnum.PUBLIC
        return FileVisibilityEnum.PRIVATE

    @property
    def allowed_mime_types(self) -> tuple[str, ...] | None:
        if self is self.FORM_FILE:
            return None
        if self is self.AVATAR:
            return ("image/png", "image/jpeg", "image/gif", "image/webp")
        return ("image/*",)

    @property
    def max_size(self) -> int:
        if self in (self.AVATAR, self.LOGO):
            return 2 * 1024 * 1024
        return (10 if self is self.FORM_IMAGE else 20) * 1024 * 1024

    def allows_mime_type(self, mime_type: str) -> bool:
        allowed = self.allowed_mime_types
        return (
            allowed is None
            or mime_type in allowed
            or ("image/*" in allowed and mime_type.startswith("image/"))
        )
