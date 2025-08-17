from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, ForeignKey
from typing import Optional, List
from datetime import datetime

# ---------- User ----------
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(sa_column=Column(Integer, default=None, primary_key=True))
    username: str = Field(sa_column=Column(String(100), index=True, unique=True, nullable=False))
    email: str = Field(sa_column=Column(String(100), index=True, unique=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String, nullable=False), exclude=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


    messages: List["Message"] = Relationship(back_populates="sender", sa_relationship_kwargs={"lazy": "selectin"})
    chatrooms: List["ChatRoomParticipant"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})


# ---------- ChatRoom ----------
class ChatRoom(SQLModel, table=True):
    __tablename__ = "chatrooms"

    id: Optional[int] = Field(sa_column=Column(Integer, default=None, primary_key=True))
    name: str = Field(sa_column=Column(String, nullable=False))
    is_private: bool = Field(default=False)
    is_direct_message: bool = Field(default=False, nullable=True, exclude=True)
    owner_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id")))

    messages: List["Message"] = Relationship(back_populates="chatroom", sa_relationship_kwargs={"lazy": "selectin"})
    participants: List["ChatRoomParticipant"] = Relationship(back_populates="chatroom", sa_relationship_kwargs={"lazy": "selectin"})


# ---------- ChatRoomParticipant ----------
class ChatRoomParticipant(SQLModel, table=True):
    __tablename__ = "chatroomparticipants"

    id: Optional[int] = Field(sa_column=Column(Integer, default=None, primary_key=True))
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id")))
    chatroom_id: int = Field(sa_column=Column(Integer, ForeignKey("chatrooms.id")))
    joined_at: datetime = Field(default_factory=datetime.now)

    user: "User" = Relationship(back_populates="chatrooms")
    chatroom: "ChatRoom" = Relationship(back_populates="participants")


# ---------- Message ----------
class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(sa_column=Column(Integer, default=None, primary_key=True))
    content: str = Field(sa_column=Column(String, nullable=False))
    timestamp: datetime = Field(default_factory=datetime.now)
    is_edited: bool = Field(default=False)

    sender_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id")))
    chatroom_id: int = Field(sa_column=Column(Integer, ForeignKey("chatrooms.id")))

    sender: "User" = Relationship(back_populates="messages")
    chatroom: "ChatRoom" = Relationship(back_populates="messages")


class BlacklistedToken(SQLModel, table=True):
    __tablename__ = "blacklistedtokens"

    id: int = Field(sa_column=Column(Integer, primary_key=True, nullable=False))
    token: str = Field(sa_column=Column(String, index=True, unique=True))
    token_jti: str = Field(sa_column=Column(String, unique=True))
    expires_at: datetime


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refreshtokens"
    
    id: Optional[int] = Field(sa_column=Column(Integer, default=None, primary_key=True))
    jti: str = Field(sa_column=Column(String, index=True, unique=True))
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id")))
    session_id: str = Field(sa_column=Column(String, index=True, unique=True))
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    revoked: bool = Field(default=False)