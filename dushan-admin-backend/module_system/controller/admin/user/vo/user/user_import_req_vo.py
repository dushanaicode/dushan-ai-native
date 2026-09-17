from fastapi import UploadFile

from framework.common.schemas.base_request_vo import BaseRequestVO


class UserImportReqVO(BaseRequestVO):
    file: UploadFile
    update_support: bool = False
