from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import init_db
from app.routers import auth, chatroom, users, message, ws_chat

version="v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting ...................")
    await init_db()
    yield
    print("Server is shutting down..")
    print("Server has been stopped........")


app = FastAPI(
    title="Real-Time Chat API",
    description="Handles everything related to chatroom management — creating rooms, listing them, joining them, and seeing who’s inside. Only authenticated users can create or join chatrooms.",
    version=version,
    lifespan=lifespan,
    docs_url=f"/api/{version}/docs",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/mit"
    },
    contact={
        "name": "Godprevail Eseh",
        "email": "esehgodprevail@gmail.com",
        "url": "https://github.com/Egcarson?tab=repositories"
    }
)


app.include_router(auth.auth_router, prefix=f"/api/{version}/auth")
app.include_router(users.user_router, prefix=f"/api/{version}")
app.include_router(chatroom.room_router, prefix=f"/api/{version}")
app.include_router(message.m_router, prefix=f"/api/{version}")
app.include_router(ws_chat.router, prefix=f"/api/{version}")



@app.get('/')
async def root():
    return {"message": "Real-Time Chat API"}