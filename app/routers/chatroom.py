from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio.session import AsyncSession
from typing import List, Optional
from app.db.database import get_session
from app.core.dependencies import get_current_user
from app.services import chatroom as room_service
from app.schemas import ChatRoomCreate, ChatRoomRead, ChatRoomParticipantRead
from app.models import User


room_router = APIRouter(
    tags=['ChatRooms']
)


@room_router.post('/chatrooms/', status_code=status.HTTP_201_CREATED)
async def create_chatroom(payload: ChatRoomCreate, response: Response, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Creates a new chatroom with the provided payload.

    Parameters:
    - payload (ChatRoomCreate): The data required to create the chatroom.
    - response (Response): Used to set the Location header upon successful creation.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - 201 CREATED: Chatroom created successfully.
    - 400 BAD REQUEST: A chatroom with the same name already exists.
    """
    
    room_check = await room_service.room_check(payload.name, session)
    if room_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sorry, the room name '{payload.name}' already exists"
        )
    
    new_room = await room_service.create_chatroom(payload, session, current_user)
    response.headers['Location'] = f"/chatrooms/{new_room.id}"

    return new_room

@room_router.get('/chatrooms/', status_code=status.HTTP_200_OK, response_model=List[ChatRoomRead])
async def get_chatrooms(skip: int = 0, limit: int=10, is_private: Optional[bool] = None, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Retrieves all available chatrooms with pagination (default limit: 10) and optional privacy filtering.

    Parameters:
    - skip (int): Number of chatrooms to skip (used for pagination).
    - limit (int): Maximum number of chatrooms to return. Must not exceed 50.
    - is_private (bool): If True, retrieves private chatrooms; if False, retrieves public chatrooms; otherwise, all chatrooms including private and public.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - List[ChatRoomRead]: A list of available chatrooms.

    Raises:
    - HTTPException:
        - 400 BAD REQUEST: If the `limit` exceeds 50.
        - 500 INTERNAL SERVER ERROR: If an error occurs while retrieving chatrooms.
    """

    MAX_LIMIT = 50
    if limit > MAX_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit cannot exceed {MAX_LIMIT}"
        )
    try:
        chatrooms = await room_service.list_chatrooms(skip, limit, session, is_private)

        return chatrooms
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured while trying to return list of chatrooms"
        )


@room_router.get('/chatrooms/{chatroom_id}', status_code=status.HTTP_200_OK, response_model=ChatRoomRead)
async def get_single_room(chatroom_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):
    
    """
    Get a single room by its ID.

    Parameters:
    - chatroom_id (int): The ID of the chatroom to retrieve.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - ChatRoomRead - The Chatroom data

    Raise:
    - HTTPException: 
        - 404 Not Found (error): If the chatroom does not exist.
    """

    chatroom = await room_service.get_single_chatroom(chatroom_id, session)

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatrooom does not exist!"
        )
    
    return chatroom


@room_router.post('/chatrooms/{chatroom_id}/members', status_code=status.HTTP_200_OK)
async def join_chatroom(chatroom_id: int, response: Response, session: AsyncSession=Depends(get_session), current_user: User = Depends(get_current_user)):
    
    """
    Adds the current authenticated user as a member of the specified chatroom.

    Parameters:
    - chatroom_id (int): The ID of the chatroom to join.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - 200 OK if the user successfully joins the chatroom.
    - 404 Not Found if the chatroom does not exist.
    - 400 Bad Request if the user is already a member of the chatroom.
    """


    chatroom = await room_service.get_single_chatroom(chatroom_id, session)

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom does not exist!"
        )
    
    #check if participant exists in the room already
    is_member = await room_service.participant_check(current_user.id, chatroom.id, session)
    if is_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already a member of '{chatroom.name}' room"
        )

    await room_service.join_room(chatroom_id, current_user, session)

    response.headers['Location'] = f"/chatrooms/{chatroom.id}/members"

    return{
        "message": f"You have successfully joined '{chatroom.name}' room.",
        "caution": "Please kindly read the room's rules and regulations."
    }


@room_router.get('/chatrooms/{chatroom_id}/members', status_code=status.HTTP_200_OK, response_model=List[ChatRoomParticipantRead])
async def get_room_members(chatroom_id: int, skip: int=0, limit: int=10, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Retrieves all members of a specified chatroom, with optional pagination.

    Parameters:
    - chatroom_id (int): ID of the chatroom whose members are to be retrieved.
    - skip (int): Number of members to skip (used for pagination).
    - limit (int): Maximum number of members to return.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - List[ChatRoomParticipantRead]: A list of members in the specified chatroom.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: Chatroom does not exist.
    """


    chatroom = await room_service.get_single_chatroom(chatroom_id, session)

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatrooom does not exist!"
        )

    members = await room_service.chatroom_participants(chatroom_id, skip, limit, session)

    return members


@room_router.delete('/chatrooms/{chatroom_id}/members/me', status_code=status.HTTP_200_OK)
async def leave_room(chatroom_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Allows the currently authenticated user to leave a chatroom by its ID.

    Parameters:
    - chatroom_id (int): ID of the chatroom to leave.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - 200 OK: User left the chatroom successfully.
    - 404 NOT FOUND: Chatroom does not exist, or user is not a member of the specified chatroom.
    """

    chatroom = await room_service.get_single_chatroom(chatroom_id, session)

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatrooom does not exist!"
        )
    
    member_check = await room_service.get_member(current_user.id, chatroom_id, session)
    if not member_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member does not exist in this room!"
        )
    
    await room_service.leave_room(current_user.id, chatroom_id, session)

    return JSONResponse(
        content={
            "message": f"You've successfully exited {chatroom.name}"
        }
    )


@room_router.delete('/chatrooms/{chatroom_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(chatroom_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Allows the currently authenticated user to delete a specified chatroom.
    
    Parameters:
    - chatroom_id (int): ID of the chatroom to be deleted.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If chatroom does not exist.
        - 403 FORBIDDEN: If the authenticated user is not the creator of the specified chatroom.
    """

    chatroom = await room_service.get_single_chatroom(chatroom_id, session)

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatrooom does not exist!"
        )
    
    if chatroom.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can not delete a room if you did not create it!"
        )
    
    await room_service.delete_room(chatroom_id, session)