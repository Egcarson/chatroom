from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio.session import AsyncSession
from fastapi.security.http import HTTPAuthorizationCredentials
from app.core.utils import verify_access_token
from app.db.database import get_session
from app.services import users as user_service
from app.core.utils import get_blacklisted_token_jti, validate_refresh_token_jti



class AccessPass(HTTPBearer):
    
    def __init__(self, auto_error: bool=True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request, session: AsyncSession=Depends(get_session)) -> HTTPAuthorizationCredentials | None:
        
        creds = await super().__call__(request)

        token = creds.credentials

        try:
            token_data = verify_access_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token."
            )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )
        
        if token_data.get('jti') is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'JTI' likly expired."
            )
        
        #check if token has been revoked
        token_jti = token_data.get('jti')
        blacklisted_token = await get_blacklisted_token_jti(token_jti, session)
        if blacklisted_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token has already been revoked (User logged out)"
            )
        
        await self.verify_token_data(token_data, session)

        return token_data

    async def verify_token_data(self, token_data):
        raise NotImplementedError("Override this method in child classes")


class AccessTokenBearer(AccessPass):

    async def verify_token_data(self, token_data: dict, session: AsyncSession):
        
        if token_data and token_data.get('refresh'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Access Token."
            )

class RefreshTokenBearer(AccessPass):

    async def verify_token_data(self, token_data: dict, session: AsyncSession):
        
        if token_data and not token_data.get('refresh'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Refresh Token."
            )
        
        refresh_jti = token_data.get('jti')
        if not refresh_jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing JTI"
            )
        
        await validate_refresh_token_jti(refresh_jti, session)


async def get_current_user(token_details: dict = Depends(AccessTokenBearer()), session: AsyncSession=Depends(get_session)):

    user_email = token_details['user']['email']

    user = await user_service.get_user_email(user_email, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )
    
    return user

refresh_token = RefreshTokenBearer()