from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.controller.admin.social.vo.user.user_bind_req_vo import SocialUserBindReqVO


class SocialUserConvert:
    @staticmethod
    def convert(user_id: int, user_type: int, req_vo: SocialUserBindReqVO) -> SocialUserBindReqDTO:
        """将 SocialUserBindReqVO 转换为 SocialUserBindReqDTO"""
        return SocialUserBindReqDTO(
            user_id=user_id,
            user_type=user_type,
            type=req_vo.type,
            code=req_vo.code,
            state=req_vo.state,
        )
