SOURCE = """
import asyncio
import json
import os
from datetime import UTC,datetime,timedelta
from pydantic import BaseModel,Field
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_di.decorators.components import service
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.decorators import controller,route
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from framework.starter_websocket.core.websocket_service import WebSocketService
from framework.starter_websocket.decorators.socket_audience import socket_audience
from framework.starter_websocket.decorators.socket_handler import socket_handler
from framework.starter_websocket.decorators.socket_event import socket_event
from framework.starter_websocket.handler.socket_handler import SocketHandler
from framework.starter_websocket.model.audience_definition import AudienceDefinition
from framework.starter_websocket.model.handler_definition import HandlerDefinition
from framework.starter_websocket.model.event_definition import EventDefinition
from framework.starter_websocket.model.socket_message import SocketMessage
from framework.starter_websocket.model.socket_target import SocketTarget
from framework.starter_websocket.spi.websocket_ticket_provider import WebSocketTicketProvider
from framework.starter_websocket.spi.socket_lifecycle_listener import SocketLifecycleListener

policy=RoutePolicy(realm=SecurityRealm.PLATFORM)
read=RoutePolicy(realm=SecurityRealm.PLATFORM,permissions=("read",))
send=RoutePolicy(realm=SecurityRealm.PLATFORM,permissions=("send",))

@socket_audience(AudienceDefinition(key="test",policy=policy,send_policy=send,workload_capability="ws:test",allow_global_targets=True))
class TestAudience:
    pass

class Payload(BaseModel):
    text: str
class WaitPayload(BaseModel):
    text: str
    fail: bool=False

@service
class Probe:
    def __init__(self):
        self.gate=asyncio.Event()
        self.received=[]; self.active=0; self.maximum=0; self.instances=[]; self.contexts=[]
        self.connects=0; self.disconnects=0
        self.block_handshake=False; self.auth_gate=asyncio.Event()

@socket_event(EventDefinition(audience="test",type="echo",payload=Payload,policy=read,projector=None))
class EchoEvent:
    pass

@socket_handler(HandlerDefinition(audience="test",type="echo",payload=Payload,policy=read))
class EchoHandler(SocketHandler):
    def __init__(self,probe: Probe): self.probe=probe
    async def handle(self,payload,context):
        self.probe.instances.append(self)
        self.probe.contexts.append(ApplicationContext.current_execution())
        self.probe.received.append(payload.text)
        await context.reply("echo",payload)

@socket_handler(HandlerDefinition(audience="test",type="wait",payload=WaitPayload,policy=read))
class WaitHandler(SocketHandler):
    def __init__(self,probe: Probe): self.probe=probe
    async def handle(self,payload,context):
        self.probe.active+=1; self.probe.maximum=max(self.probe.maximum,self.probe.active)
        self.probe.received.append(payload.text)
        try:
            await self.probe.gate.wait()
            if payload.fail: raise ValueError(payload.text)
            await context.reply("echo",Payload(text=payload.text))
        finally: self.probe.active-=1

@service(providers=(SocketLifecycleListener,))
class Listener(SocketLifecycleListener):
    audience="test"
    def __init__(self,probe: Probe): self.probe=probe
    async def connected(self,connection): self.probe.connects+=1
    async def disconnected(self,connection,code): self.probe.disconnects+=1

@service(interface=TokenProvider)
class Tokens(TokenProvider):
    def __init__(self,cache: CacheHandler,settings: WebSocketSettings):
        self.cache,self.cache_key=cache,settings.cache_key(); self.prefix="ws-tests:"+settings.namespace
    @property
    def client(self): return self.cache.get_client(self.cache_key)
    async def resolve(self,digest,*,application_id,domain):
        value=await self.client.get(self.prefix+":session:"+digest)
        return None if value is None else LoginSession.model_validate_json(value)
    async def revoke(self,identity):
        await self.client.set(self.prefix+":session:"+identity.token_digest,identity.model_copy(update={"revoked":True}).model_dump_json(),ex=600)

@service(interface=PermissionProvider)
class Permissions(PermissionProvider):
    async def snapshot(self,identity,*,binding):
        return PermissionSnapshot(binding=binding,revision=identity.authorization_revision,
            permissions=identity.scopes,roles=frozenset())

@service(interface=WorkloadProvider)
class Workloads(WorkloadProvider):
    async def authenticate(self,source,*,application_id,domain,capability,tenant_id):
        if source!="ws-test" or capability not in ("ws:test","websocket:invalidate"): raise SecurityException("denied")
        return WorkloadIdentity(application_id=application_id,domain=domain,service_id="ws-test",tenant_id=tenant_id,
            audience=source,capabilities=frozenset((capability,)),expires_at=datetime.now(UTC)+timedelta(minutes=5))

@service(interface=WebSocketTicketProvider)
class Tickets(WebSocketTicketProvider):
    def __init__(self,tokens: TokenProvider,probe: Probe): self.tokens,self.probe=tokens,probe
    async def consume(self,ticket,*,application_id,domain):
        digest=await self.tokens.client.getdel(self.tokens.prefix+":ticket:"+OpaqueToken.digest(ticket))
        if digest is None: raise SecurityException("invalid")
        if self.probe.block_handshake: await self.probe.auth_gate.wait()
        session=await self.tokens.resolve(digest,application_id=application_id,domain=domain)
        if session is None: raise SecurityException("invalid")
        return session

class SendInput(BaseModel):
    target: SocketTarget
    message: SocketMessage
class Invalidation(BaseModel):
    family_id: str|None=None
    tenant_id: str|None=None

@controller("/api/ws-test",policy=send)
class TestController:
    def __init__(self,probe: Probe,service: WebSocketService,security: SecurityService,tokens: TokenProvider):
        self.probe,self.service,self.security,self.tokens=probe,service,security,tokens
    @route("/ticket",methods=("POST",))
    async def ticket(self):
        ticket=OpaqueToken.generate()
        await self.tokens.client.set(self.tokens.prefix+":ticket:"+OpaqueToken.digest(ticket),self.security.context.require().token_digest,ex=30)
        return {"ticket":ticket,"expiresAtMs":int(datetime.now(UTC).timestamp()*1000)+30000}
    @route("/state")
    async def state(self):
        return {"pid":os.getpid(),"runtime":self.service.runtime.resources(),
            "online_prefix":None if self.service.runtime.online is None else self.service.runtime.online.prefix,
            "active":self.probe.active,"maximum":self.probe.maximum,"received":self.probe.received,
            "instances":len(self.probe.instances),"distinct_instances":len({id(item) for item in self.probe.instances}),
            "active_contexts":sum(item.active for item in self.probe.contexts),
            "connects":self.probe.connects,"disconnects":self.probe.disconnects}
    @route("/release",methods=("POST",))
    async def release(self): self.probe.gate.set(); self.probe.auth_gate.set(); return {"released":True}
    @route("/hold-handshake",methods=("POST",))
    async def hold_handshake(self): self.probe.block_handshake=True; return {"held":True}
    @route("/drop-subscription",methods=("POST",))
    async def drop_subscription(self):
        await self.service.runtime.transport.subscription.aclose()
        return {"disconnected":True}
    @route("/cancel-close-waiter",methods=("POST",))
    async def cancel_close_waiter(self):
        closing=asyncio.create_task(self.service.runtime.quiesce())
        await asyncio.sleep(0)
        closing.cancel()
        try: await closing
        except asyncio.CancelledError: return {"cancelled":True}
        raise AssertionError("close waiter unexpectedly completed")
    @route("/fail-close",methods=("POST",))
    async def fail_close(self):
        runtime=self.service.runtime
        close=runtime.transport.close
        async def failed():
            await close()
            raise OSError("controlled subscription close failure")
        runtime.transport.close=failed
        try: await runtime.quiesce()
        except ExceptionGroup as error:
            return {"error":type(error).__name__,"connections":len(runtime.connections)}
        raise AssertionError("close failure was hidden")
    @route("/send",methods=("POST",))
    async def send(self,command: SendInput):
        result=await self.security.run_workload("ws-test",lambda: self.service.send(command.target,command.message),capability="ws:test")
        return {"transport":result.transport,"accepted":result.accepted}
    @route("/online",methods=("POST",))
    async def online(self,target: SocketTarget):
        result=await self.security.run_workload("ws-test",lambda: self.service.online(target),capability="ws:test")
        return [item.model_dump() for item in result]
    @route("/invalidate",methods=("POST",))
    async def invalidate(self,command: Invalidation):
        result=await self.security.run_workload("ws-test",lambda: self.service.invalidate(family_id=command.family_id,tenant_id=command.tenant_id),capability="websocket:invalidate")
        return {"accepted":result.accepted}
"""
