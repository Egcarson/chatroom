from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio.session import AsyncSession
from typing import List
from app.schemas import UserRead, UserUpdate
from app.db.database import get_session
from app.core.dependencies import get_current_user
from app.models import User
from app.services import users as user_service


user_router = APIRouter(
    tags=["Users"]
)

@user_router.get('/users/', status_code=status.HTTP_200_OK, response_model=List[UserRead])
async def get_users(skip: int=0, limit: int=10, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Retrieve all available users with pagination (default limit = 10).

    Parameters:
    - skip (int): Number of users to skip (used for pagination).
    - limit (int): Maximum number of users to return (default is 10, with a maximum of 100).
    - session (AsyncSession): Injected asychronous databse session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - List[UserRead]: A paginated list of all available users

    Raises:
    - HTTPException:
        - 422 UNPROCESSABLE ENTITY: If 'limit' exceeds 50    
    """

    MAX_LIMIT = 100
    if limit > MAX_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Limit cannot exceed {MAX_LIMIT}"
        )
    
    users = await user_service.get_users(skip, limit, session)
        
    return users

    

@user_router.get('/users/{user_id}', status_code=status.HTTP_200_OK, response_model=UserRead)
async def get_user(user_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Get a single user by its ID.

    Parameters:
    - user_id (int): The ID of the user to retrieve.
    - session (AsyncSession): Injected asychronous databse session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - UserRead: The data of the specified user.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the specified user does not exist. 
    """

    user = await user_service.get_user(user_id, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    return user


@user_router.patch('/users/{user_id}', status_code=status.HTTP_200_OK, response_model=UserRead)
async def update_user(user_id: int, user_data: UserUpdate, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Update the specified user by their ID.

    Parameters:
    - user_id (int): The ID of the user to be updated.
    - user_data (UserUpdate): The content to update the user's information.
    - session (AsyncSession): Injected asychronous databse session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Returns:
    - UserRead: The updated user data.

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the specified user does not exist. 
        - 403 FORBIDDEN: If the currently authenticated user is not the specified user
    """

    user = await user_service.get_user(user_id, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if current_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the permission to update this user"
        )
    
    
    updated_user = await user_service.update_user(user_id, user_data, session)

    return updated_user


@user_router.delete('/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession=Depends(get_session), current_user: User=Depends(get_current_user)):

    """
    Delete the currently authenticated user account.
    
    Parameters:
    - user_id (int): ID of the user to be deleted.
    - session (AsyncSession): Injected asynchronous database session.
    - current_user (User): The currently authenticated user (injected via dependency).

    Raises:
    - HTTPException:
        - 404 NOT FOUND: If the specified user does not exist.
        - 403 FORBIDDEN: If the current user is not the same as the specified user.
    """

    user = await user_service.get_user(user_id, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if current_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted! Request aborted"
        )
    
    await user_service.delete_user(user_id, session)