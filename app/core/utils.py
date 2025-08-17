import uuid
import jwt
from fastapi import HTTPException, status
from sqlmodel import delete, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from jwt import ExpiredSignatureError, PyJWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from app.core.config import Config
from app.models import BlacklistedToken, RefreshToken


ACCESS_TOKEN_EXPIRY = 120

pwd_context = CryptContext(
    schemes=['bcrypt']
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password:str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(user_data: dict, expiry: timedelta=None, refresh: bool=False, session_id: str = None, jti:str = None):

    token_expiry = expiry if expiry is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRY)

    payload = {}

    payload['user'] = user_data
    payload['exp'] = int((datetime.now(timezone.utc) + token_expiry).timestamp())
    payload['jti'] = jti or str(uuid.uuid4())
    payload['refresh'] = refresh
    payload['session_id'] = session_id or str(uuid.uuid4())


    access_token = jwt.encode(
        payload=payload,
        key=Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM
    )

    return access_token


def verify_access_token(token: str) -> dict:

    try:

        token_data = jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET,
            algorithms=[Config.JWT_ALGORITHM]
        )

        if 'jti' not in token_data:
            raise KeyError("Token does not contain 'jti' field!")
        
        return token_data
    
    except ExpiredSignatureError:
        raise Exception("Token has expired.")
    
    except PyJWTError as e:
        raise Exception(f"Invalid token: {e}")
    

async def create_token_blacklist(token: str, session: AsyncSession):

    try:
        payload = jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET,
            algorithms=[Config.JWT_ALGORITHM]
        )

        exp_timestamp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_timestamp)
    except Exception:
        raise ValueError("Invalid token")
    
    token_jti = payload.get('jti')    
    blacklist_token = BlacklistedToken(token=token, token_jti=token_jti, expires_at=expires_at)

    session.add(blacklist_token)
    await session.commit()

async def get_blacklisted_token_jti(jti: str, session: AsyncSession):

    statement = select(BlacklistedToken).where(BlacklistedToken.token_jti == jti)

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_blacklisted_token(token: str, session: AsyncSession):

    statement = select(BlacklistedToken).where(BlacklistedToken.token == token)

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def delete_blacklisted_token(session: AsyncSession):

    now = datetime.now()

    token = delete(BlacklistedToken).where(BlacklistedToken.expires_at < now)

    await session.execute(token)
    await session.commit()


async def save_refresh_token(
        jti: str,
        user_id: int,
        session_id: str,
        expires_at: datetime,
        session: AsyncSession
        ):
    
    token = RefreshToken(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
        expires_at=expires_at
    )

    session.add(token)
    await session.commit()


async def validate_refresh_token_jti(jti: str, session:AsyncSession):

    stmt = select(RefreshToken).where(
        RefreshToken.jti == jti,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now()
        )
    
    result = await session.execute(stmt)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid of expired token"
        )
    
    return token


async def revoke_refresh_token(session_id: str, session: AsyncSession):

    stmt = select(RefreshToken).where(RefreshToken.session_id == session_id)

    result = await session.execute(stmt)

    token = result.scalar_one_or_none()

    if token:
        token.revoked = True
        await session.commit()