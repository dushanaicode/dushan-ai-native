SOURCE = """
import json
from dataclasses import asdict
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from sqlalchemy import MetaData,String,JSON,DateTime,Integer,select,insert,update,delete
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.mysql import DATETIME
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_mq.spi.outbox_provider import OutboxProvider
from framework.starter_mq.model.outbox_record import OutboxRecord
from framework.starter_mq.model.prepared_message import PreparedMessage
from framework.starter_mq.definitions.enums.outbox_state import OutboxState
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes

metadata=MetaData()
timestamp=DateTime().with_variant(DATETIME(fsp=6),"mysql")
@global_model
class Business(BaseDO):
    __tablename__="mq_business___SUFFIX__"
    metadata=metadata
    name=mapped_column(String(80),nullable=False)
@global_model
class Control(BaseDO):
    __tablename__="mq_control___SUFFIX__"
    metadata=metadata
    label=mapped_column(String(40),nullable=False)
@global_model
class Row(BaseDO):
    __tablename__="mq_outbox___SUFFIX__"
    metadata=metadata
    record_id=mapped_column(String(128),unique=True,nullable=False)
    state=mapped_column(String(30),nullable=False)
    ready=mapped_column(timestamp,nullable=False)
    expires=mapped_column(timestamp,nullable=True)
    token=mapped_column(String(40),nullable=True)
    settled_token=mapped_column(String(40),nullable=True)
    finished=mapped_column(timestamp,nullable=True)
    attempts=mapped_column(Integer,nullable=False)
    error_type=mapped_column(String(128),nullable=True)
    spec=mapped_column(JSON,nullable=False)
    receipt=mapped_column(JSON,nullable=True)

@service(interface=OutboxProvider)
class Store(OutboxProvider):
    def __init__(self,database: SessionProvider): self.database=database
    @staticmethod
    def record(row):
        return OutboxRecord(id=row.record_id,message=PreparedMessage.model_validate_json(json.dumps(row.spec)),
            state=OutboxState(row.state),attempts=row.attempts,created_at=row.create_time.replace(tzinfo=UTC),
            ready_at=row.ready.replace(tzinfo=UTC),claim_token=row.token,
            claim_expires_at=None if row.expires is None else row.expires.replace(tzinfo=UTC),
            finished_at=None if row.finished is None else row.finished.replace(tzinfo=UTC),error_type=row.error_type)
    async def insert(self,record):
        async with self.database.transaction() as session:
            await session.scalar(select(Control.id).where(Control.id==1).with_for_update())
            current=await session.scalar(select(Row.spec).where(Row.record_id==record.id))
            if current is not None:
                if current!=record.message.model_dump(mode="json"): raise MQException(MQErrorCodes.CONFLICT)
                return
            await session.execute(insert(Row).values(record_id=record.id,state=record.state.value,
                ready=record.ready_at.replace(tzinfo=None),attempts=record.attempts,
                create_time=record.created_at.replace(tzinfo=None),spec=record.message.model_dump(mode="json")))
    async def claim(self,*,now,lease_seconds,max_attempts,record_id):
        stamp=now.replace(tzinfo=None)
        async with self.database.transaction() as session:
            await session.scalar(select(Control.id).where(Control.id==1).with_for_update())
            await session.execute(update(Row).where(Row.state=="sending",Row.expires<=stamp).values(state="unknown"))
            await session.execute(update(Row).where(Row.state=="pending",Row.attempts>=max_attempts).values(state="dead",finished=stamp))
            query=select(Row).where(Row.state=="pending",Row.ready<=stamp)
            if record_id is not None: query=query.where(Row.record_id==record_id)
            row=(await session.scalars(query.order_by(Row.id).limit(1).with_for_update())).one_or_none()
            if row is None: return None
            token=uuid4().hex; expires=now+timedelta(seconds=lease_seconds)
            record=self.record(row).model_copy(update={
                "state":OutboxState.SENDING,"attempts":row.attempts+1,"claim_token":token,"claim_expires_at":expires})
            await session.execute(update(Row).where(Row.id==row.id).values(state="sending",attempts=record.attempts,
                expires=expires.replace(tzinfo=None),token=token))
        return record
    async def finish(self,record,*,state,ready_at,error_type,receipt):
        now=datetime.now(UTC)
        terminal=state not in (OutboxState.PENDING,OutboxState.SENDING)
        async with self.database.transaction() as session:
            current=await session.scalar(select(Row).where(Row.record_id==record.id).with_for_update())
            if current.state==state.value and current.token is None and current.settled_token==record.claim_token and current.receipt==(None if receipt is None else asdict(receipt)):
                return
            result=await session.execute(update(Row).where(Row.record_id==record.id,Row.state=="sending",
                Row.token==record.claim_token,Row.expires>now.replace(tzinfo=None)).values(state=state.value,
                ready=ready_at.replace(tzinfo=None),expires=None,token=None,finished=now.replace(tzinfo=None) if terminal else None,
                error_type=error_type,settled_token=record.claim_token,receipt=None if receipt is None else asdict(receipt)))
            if result.rowcount!=1: raise MQException(MQErrorCodes.LEASE)
    async def cancel(self,record_id):
        async with self.database.transaction() as session:
            result=await session.execute(update(Row).where(Row.record_id==record_id,Row.state=="pending").values(state="cancelled",finished=datetime.now(UTC).replace(tzinfo=None)))
            return result.rowcount==1
    async def cleanup(self,*,before,limit):
        async with self.database.transaction() as session:
            ids=(await session.scalars(select(Row.id).where(Row.state.in_(("published","dead","cancelled")),Row.finished<before.replace(tzinfo=None)).order_by(Row.id).limit(limit).with_for_update())).all()
            if not ids: return 0
            result=await session.execute(delete(Row).where(Row.id.in_(ids)))
            return result.rowcount
"""
