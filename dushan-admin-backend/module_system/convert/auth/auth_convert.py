from collections import defaultdict
from datetime import timezone

from framework.common.datetime.core.date_utils import DateUtils
from module_system.controller.admin.auth.vo.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.auth_permission_info_resp_vo import (
    AuthPermissionInfoRespVO,
)
from module_system.controller.admin.auth.vo.menu_vo import MenuVO
from module_system.controller.admin.auth.vo.user_vo import UserVO
from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO


class AuthConvert:
    """系统认证转换器"""

    @staticmethod
    def convert_oauth_to_auth_login_resp(access_token, date_utils: DateUtils) -> AuthLoginRespVO:
        """将 OAuth2AccessTokenDO 转换为 AuthLoginRespVO"""
        expires_time_millis = int(
            access_token.expires_time.replace(tzinfo=timezone.utc).timestamp() * 1000
        )
        return AuthLoginRespVO(
            user_id=access_token.user_id,
            access_token=access_token.access_token,
            refresh_token=access_token.refresh_token,
            expires_time=expires_time_millis,
            refresh_expires_time=int(
                access_token.refresh_expires_time.replace(tzinfo=timezone.utc).timestamp() * 1000
            ),
        )

    @staticmethod
    def convert_permission_info(
        user: AdminUserDO, roles: list[RoleDO], menus: list[MenuDO]
    ) -> AuthPermissionInfoRespVO:
        """将用户、角色、菜单信息组装为权限信息响应"""
        return AuthPermissionInfoRespVO(
            user=UserVO(
                id=user.id,
                username=user.username,
                nickname=user.nickname or "",
                avatar=user.avatar or "",
                dept_id=user.dept_id,
            ),
            roles=[role.code for role in roles],
            permissions=[menu.permission for menu in menus if menu.permission],
            menus=AuthConvert._build_menu_tree(menus),
        )

    @staticmethod
    def _convert_tree_node(menu: MenuDO) -> MenuVO:
        """MenuDO → MenuVO，字段名一致但需要空值处理"""
        return MenuVO(
            id=menu.id,
            parent_id=menu.parent_id,
            name=menu.name,
            path=menu.path or "",
            component=menu.component or "",
            component_name=menu.component_name or "",
            icon=menu.icon or "",
            visible=menu.visible,
            keep_alive=menu.keep_alive,
            always_show=menu.always_show,
            children=None,
            kind=menu.kind,
            url=menu.url,
            data_permission=menu.data_permission,
        )

    @staticmethod
    def _build_menu_tree(menu_list: list[MenuDO]) -> list[MenuVO]:
        """构建菜单树"""
        if not menu_list:
            return []
        filtered_menus = [m for m in menu_list if m.kind in {"group", "page", "link", "iframe"}]
        if not filtered_menus:
            return []
        node_list: list[MenuVO] = [AuthConvert._convert_tree_node(m) for m in filtered_menus]
        children_map = defaultdict(list)
        for node in node_list:
            parent_id = node.parent_id
            children_map[parent_id].append(node)

        def build_tree(pid: int) -> list[MenuVO]:
            tree: list[MenuVO] = []
            children_nodes = children_map.get(pid, [])
            for tree_node in sorted(children_nodes, key=lambda x: int(x.id)):
                child_tree: list[MenuVO] = build_tree(tree_node.id)
                if child_tree:
                    tree_node.children = child_tree
                tree.append(tree_node)
            return tree

        return build_tree(str(MenuDO.ID_ROOT))
