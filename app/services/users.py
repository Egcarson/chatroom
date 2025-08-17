from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from app.schemas import UserCreate, UserUpdate
from app.models import User
from app.core.utils import hash_password


async def create_user(user_data:UserCreate, session: AsyncSession):

    user_dict = user_data.model_dump(exclude_unset=True)

    new_user = User(
        **user_dict
    )

    new_user.hashed_password = hash_password(user_dict['password'])

    session.add(new_user)

    await session.commit()
    await session.refresh(new_user)

    return new_user

async def get_users(skip: int, limit: int, session: AsyncSession):

    statement = select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)

    result = await session.execute(statement)

    return result.scalars()

async def get_user(user_id: int, session: AsyncSession):

    statement = select(User).where(User.id == user_id)

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_user_email(user_email: str, session: AsyncSession):

    statement = select(User).where(User.email == user_email)

    result = await session.execute(statement)

    return result.scalar_one_or_none()

async def get_username(username: str, session: AsyncSession):
    
    statement = select(User).where(User.username == username)

    result = await session.execute(statement)

    return result.scalar_one_or_none()

async def user(username: str, email: str, session: AsyncSession):

    user = await get_user_email(email, session)
    if user:
        return user
    
    return await get_username(username, session)


async def update_user(user_id: int, user_data:UserUpdate, session: AsyncSession):

    user_to_update = await get_user(user_id, session)

    if not user_to_update:
        return None
    
    payload = user_data.model_dump(exclude_unset=True)

    for k, v in payload.items():
        setattr(user_to_update, k, v)
    
    await session.commit()

    return user_to_update

async def delete_user(user_id: int, session: AsyncSession):

    user_to_delete = await get_user(user_id, session)

    if user_to_delete:

        await session.delete(user_to_delete)

        await session.commit()
    
    else:
        return None