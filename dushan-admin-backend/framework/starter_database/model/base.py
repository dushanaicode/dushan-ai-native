from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """ORM 元数据基类；连接、Session 和监听器不存放在模型类上。"""
