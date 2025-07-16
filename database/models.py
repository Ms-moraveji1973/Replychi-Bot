from sqlalchemy import Integer, String, DateTime, BigInteger,UniqueConstraint ,ForeignKey,Boolean
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass

class TelegramUser(Base):
    __tablename__ = 'telegram_users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    total_replies_received: Mapped[int] = mapped_column(Integer, default=0)
    total_replies_sent: Mapped[int] = mapped_column(Integer, default=0)
    group_id : Mapped[int] = mapped_column(BigInteger, nullable=True)


    sent_replies = relationship(
        'ReplyRelationship',
        foreign_keys='ReplyRelationship.replier_id',
        back_populates='replier_user'
    )

    received_replies = relationship(
        'ReplyRelationship',
        foreign_keys='ReplyRelationship.replied_to_id',
        back_populates='replied_user'
    )


class ReplyRelationship(Base):
    __tablename__ = 'reply_relations'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    replier_id : Mapped[int] = mapped_column(BigInteger, ForeignKey('telegram_users.id'),nullable=False)
    replied_to_id : Mapped[int] = mapped_column(BigInteger, ForeignKey('telegram_users.id'),nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    group_id : Mapped[int] = mapped_column(BigInteger, nullable=True)


    __table_args__ = (UniqueConstraint('replier_id', 'replied_to_id', name='_replier_replied_to_uc'),)

    replier_user = relationship(
        'TelegramUser',
        foreign_keys=[replier_id],
        back_populates='sent_replies',
    )

    replied_user = relationship(
        'TelegramUser',
        foreign_keys=[replied_to_id],
        back_populates='received_replies',
    )

