from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime



# ---------- User Schemas ----------
class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')
        if not any(char.islower() for char in value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isupper() for char in value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char in "!@#$%^&*()_+[]{}|;:,.<>?/~" for char in value):
            raise ValueError('Password must contain at least one special character')
        return value


class UserUpdate(BaseModel):
    username: str

class UserRead(UserBase):
    id: int
    is_active: bool

    class ConfigDict:
        from_attributes = True

class UserOut(UserBase):
    pass

    class ConfigDict:
        from_attributes = True


# ---------- ChatRoom Schemas ----------
class ChatRoomBase(BaseModel):
    name: str
    is_private: bool = False


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoomRead(ChatRoomBase):
    id: int
    is_direct_message: bool = False
    owner_id: int

    class ConfigDict:
        from_attributes = True

class ChatRoomOut(ChatRoomBase):
    pass

    class ConfigDict:
        from_attributes = True


class ChatRoomPlusMessage(BaseModel):
    message: str
    data: ChatRoomRead


# ---------- ChatRoomParticipant Schemas ----------
class ChatRoomParticipantRead(BaseModel):
    id: int
    user_id: int
    user: UserOut
    chatroom_id: int
    chatroom: ChatRoomOut
    joined_at: datetime

    class ConfigDict:
        from_attributes = True


# ---------- Message Schemas ----------
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageUpdate(MessageBase):
    pass

class MessageRead(MessageBase):
    id: int
    sender_id: int
    chatroom_id: int
    timestamp: datetime
    is_edited: bool = False

    class ConfigDict:
        from_attributes = True


class LoginData(BaseModel):
    username: str
    password: str