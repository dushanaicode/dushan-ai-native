from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app


def create_public_app(**kwargs):
    """其他组件的测试宿主明确声明根 router 公开；Web 安全回归直接使用原工厂。"""
    app = create_app(**kwargs)
    RoutePolicy.public()(app.router)
    return app
