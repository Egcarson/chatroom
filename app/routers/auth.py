import uuid
import jwt
from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio.session import AsyncSession
from datetime import timedelta, datetime, timezone
from app.schemas import UserCreate, LoginData
from app.services import users as user_service
from app.core.dependencies import get_current_user, refresh_token
from app.core.utils import verify_password, create_access_token, create_token_blacklist, delete_blacklisted_token, get_blacklisted_token, verify_access_token, revoke_refresh_token, validate_refresh_token_jti, save_refresh_token
from app.db.database import get_session
from app.models import User
from app.core.config import Config


auth_router = APIRouter(
    tags=["Authentication"]
)



REFRESH_EXPIRY = 3

@auth_router.post('/signup', status_code=status.HTTP_201_CREATED)
async def create_account(user_data: UserCreate, response: Response, session: AsyncSession=Depends(get_session)):

    """
    Creates a new user account with a username, email, and password.

    Parameters:
    - user_data (UserCreate): The user registration data.
    - response (Response): Used to set the Location header upon successful creation.
    - session (AsyncSession): Injected asynchronous database session.

    Returns:
    - 201 CREATED: New user successfully registered.
    - 400 BAD REQUEST: A user with the given email or username already exists.
    """


    existing_email = await user_service.get_user_email(user_data.email, session)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    existing_username = await user_service.get_username(user_data.username, session)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    new_user = await user_service.create_user(user_data, session)

    response.headers['Location'] = f"/users/{new_user.id}"

    return new_user

@auth_router.post('/login', status_code=status.HTTP_200_OK)
async def login(data: LoginData, session: AsyncSession=Depends(get_session)):

    """
    Authenticates a user using their password and either username or email address.

    Parameters:
    - data (LoginData): The login credentials provided by the user.
    - session (AsyncSession): Injected asynchronous database session.

    Returns:
    - 200 OK: User logged in successfully.
    - 400 BAD REQUEST: Invalid credentials provided.
    """

    username_or_email = data.username
    password = data.password

    user = await user_service.user(username_or_email, username_or_email, session)

    if user is not None:

        #validate password
        validate_password = verify_password(password, user.hashed_password)
        if validate_password:

            session_id = str(uuid.uuid4())
            jti = str(uuid.uuid4())

            user_payload = {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email
                }

            #create access_token
            access_token = create_access_token(
                user_data=user_payload,
                session_id=session_id,
                jti=jti
            )

            #create refresh_token
            refresh_token = create_access_token(
                user_data=user_payload,
                expiry=timedelta(days=REFRESH_EXPIRY),
                refresh=True,
                session_id=session_id,
                jti=jti
            )

            #decode refresh token (refresh token = rt)
            decode_rt = jwt.decode(jwt=refresh_token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
            expires_at = datetime.fromtimestamp(decode_rt['exp'])

            #save refresh meta datas for easy revoking of token
            await save_refresh_token(
                jti=jti,
                user_id=user.id,
                session_id=session_id,
                expires_at=expires_at,
                session=session
            )

            return JSONResponse(
                content={
                    "message": "You have logged in successfully!",
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
            )
        
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid login details!"
    )



@auth_router.get('/me', status_code=status.HTTP_200_OK)
async def current_user(me: User = Depends(get_current_user)):

    """
    Retrieves the currently authenticated user's details.

    Parameters:
    - me (User): The current user object, injected via dependency.

    Returns:
    - 200 OK: The authenticated user's information.
    """
    return me

auth_scheme = HTTPBearer()
@auth_router.post('/logout', status_code=status.HTTP_200_OK)
async def logout(bg_task: BackgroundTasks, credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), session: AsyncSession = Depends(get_session)):

    """
    Logs the user out by revoking their access token via blacklisting.
    
    This endpoint extracts the user's bearer token from the Authorization header,
    validates it, and adds it to a blacklist to prevent further use.
    
    Parameters:
    - bg_task (BackgroundTasks): Schedules background tasks, such as deleting expired blacklisted tokens from the database.
    - credentials (HTTPAuthorizationCredentials): Parsed bearer token from the Authorization header, used to identify and revoke the session.
    - session (AsyncSession): Injected asynchronous database session.

    Returns:
    - 200 OK: Token was successfully blacklisted; user is logged out.
    - 410 GONE: Token has already been revoked; user is already logged out.
    - 400 BAD REQUEST: Token is missing a session identifier, is invalid, or malformed.
    """

    token = credentials.credentials

    #will not be neccessary just to control exceptions for ease dev exprience
    revoked_token = await get_blacklisted_token(token, session)
    if revoked_token:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="User already logged out"
        )

    try:
        token_data = verify_access_token(token)

        session_id = token_data.get('session_id')
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is missing session_id"
            )
        
        await create_token_blacklist(token, session)

        await revoke_refresh_token(session_id, session)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    bg_task.add_task(delete_blacklisted_token, session)

    return {"Message": "Logged out successfully"}

@auth_router.get('/access_token', status_code=status.HTTP_200_OK)
async def get_new_token(token_details: dict = Depends(refresh_token), session: AsyncSession=Depends(get_session)):

    """
    Generates a new access token using a valid refresh token.

    This endpoint allows users to obtain a fresh access token when the current one has expired,
    helping maintain an active session without requiring re-authentication.

    Parameters:
    - token_details (dict): Information extracted from the validated refresh token (injected via dependency).
    - session (AsyncSession): Injected asynchronous database session.

    Returns:
    - 200 OK: A new access token if the refresh token is valid.
    - 403 FORBIDDEN: If the refresh token is invalid or expired.
    """

    expiry_time = token_details['exp']

    user = token_details.get('user')
    session_id = token_details.get('session_id')
    jti = token_details.get('jti')

    await validate_refresh_token_jti(jti, session)

    if datetime.fromtimestamp(expiry_time, tz=timezone.utc) > datetime.now(tz=timezone.utc):

        new_access_token = create_access_token(
            user_data=user,
            session_id=session_id
        )

        return JSONResponse(
            content={
                "message": "new access_token",
                "access_token": new_access_token
            }
        )
    
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail="Invalid or expired refresh token"
    )