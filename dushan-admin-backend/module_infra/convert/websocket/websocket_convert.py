from framework.starter_di.decorators.components import util
from framework.starter_di.decorators.inject import Inject
from framework.starter_websocket.config.websocket_settings import WebSocketSettings


@util
class WebSocketConvert:
    settings: WebSocketSettings = Inject()

    def build_status_info(self, active_connection_count):
        return {
            "enabled": self.settings.enabled,
            "path": self.settings.path,
            "sender_type": self.settings.transport.code,
            "login_required": True,
            "active_connections": active_connection_count,
        }
