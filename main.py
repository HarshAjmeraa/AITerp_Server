# main.py
from fastapi import FastAPI
from router import attendee, avatar, session, socket_server
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    attendee.router, 
    prefix="/attendees", 
    tags=["Attendees"])

app.include_router(
    avatar.router, 
    prefix="/avatars", 
    tags=["Avatars"])

app.include_router(
    session.router, 
    prefix="/sessions", 
    tags=["Sessions"])

# Mount the combined ASGI app (FastAPI + Socket.IO)
app.mount('/socket.io', socket_server.socket_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8181)
