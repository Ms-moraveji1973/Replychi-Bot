from sqlalchemy import Integer, String, DateTime, BigInteger,UniqueConstraint ,ForeignKey,Boolean
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional , List

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

    group_memberships : Mapped[List['GroupMemberShipRelation']] = relationship(back_populates='user',
                                                                              cascade='all, delete-orphan')


class GroupMemberShipRelation(Base):
    __tablename__ = 'group_relations'
    id : Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True, nullable=False)
    user_id : Mapped[int] = mapped_column(ForeignKey('telegram_users.id',ondelete='CASCADE'),nullable=False)
    group_id : Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'group_id', name='_user_group_uc'),)

    user : Mapped['TelegramUser'] = relationship(back_populates='group_memberships')

    sent_replies_through_membership : Mapped[List['ReplyRelationship']] = relationship(
        foreign_keys='ReplyRelationship.replier_id',
        back_populates='replier_user',
        cascade='all, delete-orphan'
    )

    receive_replies_through_membership : Mapped[List['ReplyRelationship']] = relationship(
        foreign_keys='ReplyRelationship.replied_to_id',
        back_populates='replied_user',
        cascade='all, delete-orphan'
    )


class ReplyRelationship(Base):
    __tablename__ = 'reply_relations'
    id: Mapped[int] = mapped_column(BigInteger,primary_key=True,unique=True)
    replier_id : Mapped[int] = mapped_column(BigInteger, ForeignKey('group_relations.id',ondelete='CASCADE'),nullable=False)
    replied_to_id : Mapped[int] = mapped_column(BigInteger, ForeignKey('group_relations.id',ondelete='CASCADE'),nullable=False)
    reply_count : Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint('replier_id', 'replied_to_id', name='_replier_replied_to_uc'),)


    replier_user : Mapped['GroupMemberShipRelation'] = relationship(
        'GroupMemberShipRelation',
        foreign_keys=[replier_id],
        back_populates='sent_replies_through_membership',
    )

    replied_user : Mapped['GroupMemberShipRelation'] = relationship(
        'GroupMemberShipRelation',
        foreign_keys=[replied_to_id],
        back_populates='receive_replies_through_membership',
    )


