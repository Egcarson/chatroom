from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, func
from sqlalchemy.orm import selectinload, aliased
from typing import Optional
from app.schemas import ChatRoomCreate
from app.models import ChatRoom, User, ChatRoomParticipant

"""
Basic Endpoints
create a chatroom
list all chatrooms
get single chatroom
join a chatroom
list users in a chatroom
"""

async def create_chatroom(payload: ChatRoomCreate, session: AsyncSession, current_user: User):

    room_dict = payload.model_dump(exclude_unset=True)

    new_chatroom = ChatRoom(**room_dict, owner_id=current_user.id)
    session.add(new_chatroom)
    await session.commit()
    await session.refresh(new_chatroom)

    #add creator as participant
    new_participant = ChatRoomParticipant(user_id=current_user.id, chatroom_id=new_chatroom.id)
    session.add(new_participant)
    await session.commit()
    await session.refresh(new_participant)

    return new_chatroom


async def list_chatrooms(skip: int, limit: int, session: AsyncSession, is_private: Optional[bool]=None):

    stmt = select(ChatRoom).offset(skip).limit(limit)

    if is_private is True:
        stmt = stmt.where(ChatRoom.is_private == True)
    elif is_private is False:
        stmt = stmt.where(ChatRoom.is_private == False)
    
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_single_chatroom(chatroom_id: int, session: AsyncSession):

    stmt = select(ChatRoom).where(ChatRoom.id == chatroom_id)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def join_room(chatroom_id: int, current_user: User, session: AsyncSession):

    participant = ChatRoomParticipant(user_id=current_user.id, chatroom_id=chatroom_id)
    session.add(participant)
    await session.commit()
    await session.refresh(participant)
    
    return participant

async def chatroom_participants(chatroom_id: int, skip: int, limit: int, session: AsyncSession):

    stmt = select(ChatRoomParticipant).where(ChatRoomParticipant.chatroom_id==chatroom_id).offset(skip).limit(limit).options(selectinload(ChatRoomParticipant.user), selectinload(ChatRoomParticipant.chatroom))

    participants = await session.execute(stmt)

    return participants.scalars().all()


async def room_check(room_name: str, session: AsyncSession):

    result = await session.execute(
        select(ChatRoom).where(ChatRoom.name == room_name)
    )

    return result.scalar_one_or_none()

async def participant_check(user_id: int, chatroom_id: int, session: AsyncSession):

    result = await session.execute(select(ChatRoomParticipant).where(ChatRoomParticipant.user_id == user_id, ChatRoomParticipant.chatroom_id ==chatroom_id))

    return result.scalar_one_or_none()

async def get_member(user_id: int, chatroom_id: int, session: AsyncSession):

    stmt = select(ChatRoomParticipant).where(ChatRoomParticipant.user_id == user_id, ChatRoomParticipant.chatroom_id==chatroom_id)

    result = await session.execute(stmt)

    member = result.scalar_one_or_none()

    return member


async def leave_room(user_id: int, chatroom_id: int, session: AsyncSession):

    """
    User leaves a ChatRoom
    """

    user_leaving = await get_member(user_id, chatroom_id, session)

    if user_leaving:

        await session.delete(user_leaving)
        await session.commit()
    else:
        return None
    

async def delete_room(chatroom_id: int, session: AsyncSession):

    """
    Deletes ChatRoom with it's ID
    """

    room_to_delete = await get_single_chatroom(chatroom_id, session)

    if room_to_delete:

        await session.delete(room_to_delete)

        await session.commit()
    
    else:
        return None
    

async def dms_check(receiver_id: int, current_user: int, session: AsyncSession):

    """
    Returns direct message room shared by only the current_user and receiver
    """

    subquery = (
        select(ChatRoomParticipant.chatroom_id)
        .where(ChatRoomParticipant.user_id.in_([current_user, receiver_id]))
        .group_by(ChatRoomParticipant.chatroom_id)
        .having(func.count(func.distinct(ChatRoomParticipant.user_id)) == 2)
        .subquery()
    )

    stmt = (
        select(ChatRoom)
        .join(subquery, subquery.c.chatroom_id == ChatRoom.id)
        .where(ChatRoom.is_direct_message.is_(True))
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def new_dm(reciever_id: int, current_user: int, session: AsyncSession):

    """
    Creates a new DM chat room between current_user and reciever only
    """

    new_dm = ChatRoom(
        name=f"DM-{current_user}-{reciever_id}",
        is_private=True,
        is_direct_message=True,
        owner_id=current_user
    )

    session.add(new_dm)
    await session.flush()

    #Add both participants
    session.add_all([
        ChatRoomParticipant(user_id=current_user, chatroom_id=new_dm.id),
        ChatRoomParticipant(user_id=reciever_id, chatroom_id=new_dm.id)
    ])
    
    await session.commit()
    await session.refresh(new_dm)

    return new_dm