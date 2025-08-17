# Real-Time Chat API (FastAPI + WebSockets)

A real-time chat backend built with **FastAPI**, **SQLModel**, and **WebSockets**.  
This project demonstrates advanced backend concepts like **user authentication**, **chatrooms**, **direct messages (DMs)**, and **live WebSocket broadcasting**.

---

## 🚀 Features
- **User Authentication** with JWT tokens  
- **Chatrooms** (group and direct/private chats)  
- **Messages API** (RESTful endpoints for creating and retrieving messages)  
- **Real-Time Messaging** with WebSockets (messages broadcast instantly to all participants in a chatroom)  
- **Connection Manager** for handling multiple active WebSocket connections  
- **PostgreSQL + SQLModel ORM** for persistence  

---

## 🛠 Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/)  
- [SQLModel](https://sqlmodel.tiangolo.com/)  
- [PostgreSQL](https://www.postgresql.org/)  
- [WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)  

---


## ⚙️ Setup & Installation

### 1. Clone repository
```bash
git clone https://github.com/Egcarson/chatroom.git
cd chatroom
```

### 2. Create & activate virtualenv
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Create a `.env` file with:
```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/chatdb
SECRET_KEY=supersecret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Run migrations (if using Alembic)
```bash
alembic upgrade head
```

### 6. Start server
```bash
uvicorn app.main:app --reload
```

---

## 📡 API Endpoints

### REST Endpoints
- **POST** `/api/v1/auth/login` → Get JWT token  
- **POST** `/api/v1/chatrooms/` → Create chatroom  
- **GET** `/api/v1/chatrooms/` → List chatrooms  
- **POST** `/api/v1/chatrooms/{chatroom_id}/messages` → Send message (broadcasts to WS clients)  
- **GET** `/api/v1/chatrooms/{chatroom_id}/messages` → Fetch chat history  

### WebSocket Endpoint
- **WS** `/ws/chatrooms/{chatroom_id}`  
  - Connect with a JWT token (via `Authorization: Bearer <token>` header)  
  - Send messages as JSON:  
    ```json
    {
      "content": "Hello everyone!"
    }
    ```
  - Receive real-time broadcasts instantly.  

---

## 🧪 Testing

### With Postman
- Use the **WebSocket tab** in Postman.  
- Connect to:  
  ```
  ws://localhost:8000/ws/chatrooms/{chatroom_id}
  ```
- Add `Authorization: Bearer <token>` header.  
- Send and receive JSON messages in real-time.

### With cURL (REST)
```bash
curl -X POST http://localhost:8000/api/v1/chatrooms/1/messages   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"content": "Hello from REST!"}'
```

---

## 🎯 Learning Goals
This project is designed to showcase:
- How to combine **REST APIs** + **WebSockets** in one app.  
- How to manage real-time connections with a **ConnectionManager**.  
- How to authenticate users in WebSockets with **JWT**.  
- How to structure a scalable **FastAPI project**.  

---

## 📌 Next Steps (Possible Extensions)
- Add **message delivery receipts** (seen/unseen).  
- Add **typing indicators**.  
- Add **file/image sharing** in chat.  
- Add **notifications** for offline users.  

---

## 👨‍💻 Author
Built by Godprevail
