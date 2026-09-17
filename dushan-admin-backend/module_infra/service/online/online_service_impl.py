from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_infra.controller.admin.online.vo.online_resp_vo import OnlineInfoRespVO
from module_infra.service.online.online_service import OnlineService
from module_system.api.oauth2.oauth2_session_api import OAuth2SessionApi


@service(interface=OnlineService)
class OnlineServiceImpl(OnlineService):
    sessions: OAuth2SessionApi = Inject()

    async def get_online_list(self, request):
        rows = await self.sessions.list_sessions()
        ip = "127.0.0.1" if request.ipaddr == "内网IP" else request.ipaddr
        return [
            OnlineInfoRespVO(
                token_id=row.family_id,
                user_name=row.nickname or row.username,
                dept_name=row.dept_name,
                ipaddr=row.ipaddr,
                login_location=row.login_location,
                browser=row.browser,
                os=row.os,
                login_time=row.login_time,
            )
            for row in rows
            if (not ip or row.ipaddr == ip)
            and (not request.user_name or request.user_name in {row.username, row.nickname})
        ]

    async def force_logout(self, token_id):
        await self.sessions.revoke_session(token_id)
