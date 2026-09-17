from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from uuid import uuid4

from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage
from module_system.config.system_settings import SystemSettings
from module_system.service.auth.system_message_service import SystemMessageService
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=SystemMessageService)
class SystemMessageServiceImpl(SystemMessageService):
    settings: SystemSettings = Inject()
    tokens: OAuth2TokenService = Inject()
    workloads: SystemWorkloadService = Inject()

    def _key(self):
        secret = self.settings.message_signing_key
        if secret is None or len(secret.get_secret_value()) < 32:
            raise SecurityException("configuration")
        return secret.get_secret_value()

    def _issue(self, identity, payload, audience, **claims):
        now = int(datetime.now(timezone.utc).timestamp())
        values = {
            "iss": identity.application_id,
            "domain": identity.domain,
            "aud": audience,
            "iat": now,
            "exp": min(
                now + self.settings.message_lifetime_seconds, int(identity.expires_at.timestamp())
            ),
            "jti": uuid4().hex,
            "payload": hashlib.sha256(payload).hexdigest(),
            **claims,
        }
        return jwt.encode({"alg": "HS256"}, values, OctKey.import_key(self._key().encode())).encode(
            "ascii"
        )

    def _verify(self, proof, payload, application_id, domain, audience):
        try:
            claims = jwt.decode(
                proof.decode("ascii"), OctKey.import_key(self._key().encode()), algorithms=["HS256"]
            ).claims
            jwt.JWTClaimsRegistry(
                iss={"essential": True, "value": application_id},
                aud={"essential": True, "value": audience},
                domain={"essential": True, "value": domain},
                exp={"essential": True},
                iat={"essential": True},
                jti={"essential": True},
                payload={"essential": True},
                kind={"essential": True},
            ).validate(claims)
        except (JoseError, UnicodeDecodeError) as error:
            raise SecurityException("invalid", cause=error) from error
        if claims["domain"] != domain or not hmac.compare_digest(
            claims["payload"], hashlib.sha256(payload).hexdigest()
        ):
            raise SecurityException("invalid")
        return claims

    async def issue(self, session, payload, *, audience):
        return self._issue(
            session,
            payload,
            audience,
            kind="session",
            digest=session.token_digest,
            family=session.family_id,
        )

    async def verify(self, proof, payload, *, application_id, domain, audience):
        claims = self._verify(proof, payload, application_id, domain, audience)
        if claims["kind"] != "session":
            raise SecurityException("invalid")
        session = await self.tokens.resolve_session(
            claims["digest"], application_id=application_id, domain=domain
        )
        if session is None or session.family_id != claims["family"]:
            raise SecurityException("invalid")
        return session

    async def issue_workload(self, identity, payload, *, audience, capability):
        if capability not in identity.capabilities:
            raise SecurityException("denied")
        return self._issue(
            identity,
            payload,
            audience,
            kind="workload",
            source=identity.audience,
            capability=capability,
            tenant=identity.tenant_id,
        )

    async def verify_workload(self, proof, payload, *, application_id, domain, audience):
        claims = self._verify(proof, payload, application_id, domain, audience)
        if claims["kind"] != "workload":
            raise SecurityException("invalid")
        current = await self.workloads.authenticate(
            claims["source"],
            application_id=application_id,
            domain=domain,
            capability=claims["capability"],
            tenant_id=claims["tenant"],
        )
        identity = WorkloadIdentity(
            application_id=application_id,
            domain=domain,
            service_id=current.service_id,
            tenant_id=current.tenant_id,
            audience=audience,
            capabilities=frozenset({claims["capability"]}),
            expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc),
        )
        return WorkloadMessage(identity=identity, capability=claims["capability"])
