import io
import base64
import socketio
from db import get_db_connection, pyodbc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioDataStream, SpeechSynthesisOutputFormat, ResultReason
import asyncio
from collections import deque


# Create FastAPI app
app = FastAPI()

# Add CORS middleware to the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a new Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')

# Wrap the Socket.IO server with the ASGI app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Initialize rooms dictionary
rooms = {}
currently_speaking_user = None
is_audio_playing = False

# Azure Speech Configurations
speech_config = SpeechConfig(subscription="a446630e73514d779093ab5621f15304", region="eastus")
speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)

# Function to synthesize speech with voice_code
async def synthesize_speech(text, voice_code=None, language="en-US"):
    speech_config.speech_synthesis_language = language
    if voice_code:
        speech_config.speech_synthesis_voice_name = voice_code
    
    synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == ResultReason.SynthesizingAudioCompleted:
        audio_data = result.audio_data
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        return base64_audio
    else:
        print(f"Speech synthesis failed with reason: {result.reason}")
        return None


def get_voice_code_from_room_code(room_code):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT avatar_id FROM tbl_aiterp_Sessions WHERE session_id = ?", room_code)
            session_result = cursor.fetchone()
            if session_result:
                avatar_id = session_result[0]
                cursor.execute("SELECT voice_code FROM tbl_aiterp_Avatars WHERE avatar_id = ?", avatar_id)
                avatar_result = cursor.fetchone()
                if avatar_result:
                    return avatar_result[0]
                else:
                    print(f"No avatar found with avatar_id: {avatar_id}")
                    return None
            else:
                print(f"No session found with session_id: {room_code}")
                return None
    except pyodbc.Error as e:
        print(f"Database error: {e}")
        return None


# Event handler when a new client connects
@sio.event
async def connect(sid, environ):
    print(f'New client connected: {sid}')

# Event handler when a client joins a room
@sio.event
async def join(sid, data):
    room_code = data.get('roomCode')
    username = data.get('username')

    if not room_code:
        print('Room code is missing')
        return

    if room_code not in rooms:
        rooms[room_code] = []

    existing_client = next((client for client in rooms[room_code] if client['username'] == username), None)
    if existing_client:
        print(f'User {username} rejoined room {room_code}')
        return

    rooms[room_code].append({'sid': sid, 'username': username})
    await sio.enter_room(sid, room_code)
    print(f'User {username} joined room {room_code}')

    await sio.emit('userJoined', {'username': username}, room=room_code)

# Event handler for receiving transcriptions and handling synthesized audio
@sio.event
async def transcription(sid, data):
    global currently_speaking_user, is_audio_playing

    room_code = data.get('roomCode')
    username = data.get('username')
    transcription = data.get('transcription')
    language = data.get('language', 'en-US')  

    if not room_code:
        print('Room code is missing')
        return

    # If someone else is speaking or synthesized audio is playing, reject the request
    if currently_speaking_user and currently_speaking_user != username:
        await sio.emit('speakDenied', {'reason': 'Another user is speaking or synthesized audio is playing.'}, room=sid)
        return

    # Mark the user as currently speaking
    currently_speaking_user = username
    is_audio_playing = True

    # Fetch the voice_code using the room_code (session_id)
    voice_code = get_voice_code_from_room_code(room_code)

    if not voice_code:
        print(f"Voice code not found for room {room_code}")
        currently_speaking_user = None  # Reset speaker
        is_audio_playing = False
        return

    # Synthesize speech and get Base64-encoded audio
    base64_audio = await synthesize_speech(transcription, voice_code, language)

    if base64_audio:
        await sio.emit('synthesizedAudio', {'username': username, 'audio': base64_audio}, room=room_code)
        print(f'Transcription from {username} in room {room_code} has been synthesized and broadcasted.')

    # Once the audio is broadcasted, allow others to speak
    currently_speaking_user = None
    is_audio_playing = False
    
# When a client starts speaking
@sio.event
async def startSpeaking(sid, data):
    room_code = data.get('roomCode')
    username = data.get('username')
    
    if room_code in current_speaker and current_speaker[room_code] != username:
        # Notify that someone else is speaking
        await sio.emit('speakingLocked', {'message': 'Someone else is speaking'}, to=sid)
        return

    current_speaker[room_code] = username
    await sio.emit('speakingStatus', {'username': username, 'status': 'started'}, room=room_code)

@sio.event
async def stopSpeaking(sid, data):
    room_code = data.get('roomCode')
    username = data.get('username')

    if current_speaker.get(room_code) == username:
        current_speaker.pop(room_code, None)
        await sio.emit('speakingStatus', {'username': username, 'status': 'stopped'}, room=room_code)

# Event handler for when a client leaves a room
@sio.event
async def leave(sid, data):
    room_code = data.get('roomCode')
    username = data.get('username')

    if not room_code:
        print('Room code is missing')
        return

    await sio.leave_room(sid, room_code)
    rooms[room_code] = [client for client in rooms[room_code] if client['username'] != username]

    await sio.emit('userLeft', {'username': username}, room=room_code)

    if not rooms[room_code]:
        del rooms[room_code]
        print(f'Room {room_code} is empty and has been deleted.')

    print(f'User {username} left room {room_code}')

# Event handler when a client disconnects
@sio.event
async def disconnect(sid):
    print(f'Client disconnected: {sid}')
    for room_code, clients in list(rooms.items()):
        rooms[room_code] = [client for client in clients if client['sid'] != sid]

        disconnected_client = next((client for client in clients if client['sid'] == sid), None)
        if disconnected_client:
            await sio.emit('userLeft', {'username': disconnected_client['username']}, room=room_code)

        if not rooms[room_code]:
            del rooms[room_code]
            print(f'Room {room_code} is empty and has been deleted.')
