from fastapi import UploadFile

from framework.common.schemas import BaseRequestVO


class UserImportReqVO(BaseRequestVO):
    file: UploadFile
    update_support: bool = False
