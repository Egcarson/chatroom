from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse, Response
from typing import List
from sqlalchemy.ext.asyncio.session import AsyncSession
from app.schemas import MessageRead, MessageCreate, MessageUpdate, ChatRoomRead, ChatRoomPlusMessage
from app.db.database import get_session
from app.core.dependencies import get_current_user
from app.core.connection_manager import manager
from app.services import message as m_service, chatroom as room_service, users as user_service
from app.models import User



m_router = APIRouter(
    tags=['Messages']
)

@m_router.post('/chatrooms/{chatroom_id}/messages', status_code=status.HTTP_201_CREATED, response_model=MessageRead, tags=['ChatRooms'])
async def send_message(payload: MessageCreate, chatroom_id: int, response: Response, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Send a message to a specified chatroom.

    Parameters:
    - payload (MessageCreate): The message content and metadata to be sent.
    - chatroom_id (int): ID of the chatroom to send the message to.
    - response (Response): Used to set the 'Location' header upon successful creation.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - MessageRead: The created newly created message data.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the chatroom does not exist
        - 403 FORBIDDEN: If the current user is not a member of the specified chatroom
    """

    #check if room exists
    room = await room_service.get_single_chatroom(chatroom_id, session)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom does not exist"
        )
    
    #check if the user sending message belong to the group
    participant = await room_service.participant_check(current_user.id, chatroom_id, session)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not a participant of {room.name}. Please join {room.name} to send message!"
        )
    
    #create message
    new_message = await m_service.send_message(payload, room.id, current_user.id, session)

    response.headers["Location"] = f"/messages/{new_message.id}"

    await manager.broadcast(
        chatroom_id,
        {
            "type": "message",
            "sender": current_user.username,
            "content": new_message.content,
            "timestamp": str(new_message.timestamp),
        }
    )

    return new_message


@m_router.get('/chatrooms/{chatroom_id}/messages', status_code=status.HTTP_200_OK, response_model=List[MessageRead], tags=['ChatRooms'])
async def get_messages(chatroom_id: int, skip: int=0, limit:int=10, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Retrieves all messages in the specified chatroom.

    Parameters:
    - chatroom_id (int): ID of the chatroom to retrieve messages from.
    - skip (int): Number of messages to skip (used for pagination).
    - limit (int): Maximum number of messages to return.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - List[MessageRead]: The list of messages in the specified chatroom.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the chatroom does not exist.
        - 403 FORBIDDEN: If the currently authenticated user is not a member of the specified chatroom.
    """

    #check if room exists
    room = await room_service.get_single_chatroom(chatroom_id, session)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom does not exist"
        )
    
    #check if the user sending message belong to the group
    participant = await room_service.participant_check(current_user.id, chatroom_id, session)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not a participant of {room.name}. Please join {room.name} to view messages!"
        )
    
    #get messages
    messages = await m_service.get_messages(chatroom_id, skip, limit, session)

    return messages


@m_router.patch('/messages/{message_id}', status_code=status.HTTP_200_OK, response_model=MessageRead)
async def edit_message(message_id: int, payload: MessageUpdate, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Edit a message by its ID. Only the sender is allowed to edit the message.

    Parameters:
    - message_id (int): ID of the message to be edited.
    - payload (MessageUpdate): The updated message content.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - MessageRead: The updated message data.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the specified message does not exist.
        - 403 FORBIDDEN: If the current user is not the sender of the message.
    """

    #check if message exists
    message = await m_service.get_message(message_id, session)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message does not exist"
        )
    
    #ensure the current user is the sender
    if current_user.id != message.sender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You can only edit message you sent!"
        )
    
    #edit message
    new_message = await m_service.edit_message(message_id, payload.content, session)

    return new_message


@m_router.delete('/messages/{message_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Delete a message by its ID. Only the sender of is allowed to delete the message.

    Parameters:
    - message_id (int): ID of the message to be deleted.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the specified message does not exist.
        - 403 FORBIDDEN: If the current user is not the sender of the message. 
    """

    #check if message exists
    message = await m_service.get_message(message_id, session)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message does not exist"
        )
    
    #ensure the current user is the sender
    if current_user.id != message.sender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You can only delete message you sent!"
        )
    
    await m_service.delete_message(message_id, session)


@m_router.post('/dms/{reciever_id}', status_code=status.HTTP_201_CREATED, response_model=ChatRoomPlusMessage, tags=['Direct Message'])
async def direct_message(receiver_id: int, current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):

    """
    Create or retrieve a direct message (DM) chat beween the current user and another user (receiver)

    Parameters:
    - receiver_id (int): ID of the user receiving the message.
    - current_user (User): The currently authenticated user sending the message.
    - session (AsyncSession): Injected asynchronous database session.

    Returns:
    - ChatRoomPlusMessage: The existing or newly created DM chat content between the current user and the receiver.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the reciever does not exist.
        - 400 BAD REQUEST: If the current user tries to DM themselves.
    """

    user = await user_service.get_user(receiver_id, session)

    #Check if receiver exits
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    #Prevent DM with self
    if current_user.id == receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sorry you can not DM yourself"
        )
    
    #Check if DM already exists
    existing_dms = await room_service.dms_check(receiver_id, current_user.id, session)
    if existing_dms:
        return {
            "message": f"Hey {current_user.username}, you have an opened DM with {user.username}.",
            "data": existing_dms
        }
        
    new_dm = await room_service.new_dm(receiver_id, current_user.id, session)

    return {
        "message": f"Hey {current_user.username}, you've started a DM with {user.username} - Say Hi",
        "data": new_dm
    }