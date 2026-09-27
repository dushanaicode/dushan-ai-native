import hashlib
import json

from framework.starter_security.model.login_session import LoginSession


class IdentityBinding:
    """身份绑定键的唯一计算契约；字段与顺序共同决定权限缓存隔离。"""

    @staticmethod
    def build(session: LoginSession) -> str:
        values = [
            session.application_id,
            session.domain,
            session.account_id,
            session.session_id,
            session.family_id,
            session.realm.value,
            session.tenant_id,
            session.membership_id,
            session.authority_tenant_id,
            session.authority_membership_id,
            session.platform_operator_id,
            session.support_session_id,
            None if session.access_mode is None else session.access_mode.value,
            session.group_id,
            session.management_relation_id,
            session.approved_resource,
            session.approved_action,
        ]
        return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()
