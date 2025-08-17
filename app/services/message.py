from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select, asc
from app.models import Message
from app.schemas import MessageCreate


"""
POST /messages/ → send a message

GET /messages/{chatroom_id} → get all messages in a chatroom (with optional pagination)

(Optional) PATCH /messages/{message_id} → edit a message

(Optional) DELETE /messages/{message_id} → delete a message
"""

async def send_message(payload: MessageCreate, chatroom_id: int, user_id: int, session: AsyncSession):

    new_message = Message(
        content=payload.content,
        chatroom_id=chatroom_id,
        sender_id=user_id
    )

    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)

    return new_message


async def get_messages(chatroom_id: int, skip: int, limit:int, session: AsyncSession):

    stmt = select(Message).where(Message.chatroom_id == chatroom_id).offset(skip).limit(limit).order_by(asc(Message.timestamp))

    result = await session.execute(stmt)

    messages = result.scalars().all()

    return messages

async def get_message(message_id: int, session: AsyncSession):

    stmt = select(Message).where(Message.id == message_id)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()

async def edit_message(message_id: int, content: str, session: AsyncSession):

    message = await get_message(message_id, session)

    if message is not None:

        message.content = content
        message.is_edited = True

        await session.commit()

        return message
    else:
        return None

async def delete_message(message_id: int, session: AsyncSession):

    message = await session.get(Message, message_id)

    if message is not None:

        await session.delete(message)

        await session.commit()
    
    else:
        return None