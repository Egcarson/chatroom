import jwt
from jwt import PyJWTError
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.ext.asyncio.session import AsyncSession
from app.core.connection_manager import manager
from app.models import Message, ChatRoom, User
from app.schemas import MessageCreate
from app.db.database import get_session
from app.core.utils import verify_access_token
from app.core.dependencies import get_current_user
from app.core.config import Config

router = APIRouter(
    tags=["Websockets"]
)

@router.websocket("/ws/chatrooms/{chatroom_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chatroom_id: int,
    session: AsyncSession = Depends(get_session)
):
    
    token = websocket.headers.get("Authorization")

    if not token or not token.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    token = token.split(" ")[1]

    try:
        payload = jwt.decode(jwt=token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])

        current_user = payload.get("user")

        if not current_user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect the user
    await manager.connect(chatroom_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # Save message to DB
            new_message = Message(
                chatroom_id=chatroom_id,
                sender_id=current_user["user_id"],
                content=data["content"]
            )
            session.add(new_message)
            await session.commit()
            await session.refresh(new_message)

            # Broadcast to everyone in the chatroom
            await manager.broadcast(chatroom_id, {
                "sender": current_user["username"],
                "content": new_message.content,
                "timestamp": new_message.timestamp.isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(chatroom_id, websocket)
