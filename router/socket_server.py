import io
import base64
import socketio
from db import get_db_connection, pyodbc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioDataStream, SpeechSynthesisOutputFormat, ResultReason

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

# Speech lock information for rooms
speaking_status = {}


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
        speaking_status[room_code] = {'isSpeaking': False, 'isSynthesizedAudioPlaying': False}


    existing_client = next((client for client in rooms[room_code] if client['username'] == username), None)
    if existing_client:
        print(f'User {username} rejoined room {room_code}')
        return

    rooms[room_code].append({'sid': sid, 'username': username})
    await sio.enter_room(sid, room_code)
    print(f'User {username} joined room {room_code}')

    await sio.emit('userJoined', {'username': username}, room=room_code)

# Handle synthesized audio and prevent users from speaking during audio playback
@sio.event
async def transcription(sid, data):
    room_code = data.get('roomCode')
    transcription = data.get('transcription')
    voice_code = get_voice_code_from_room_code(room_code)

    # Synthesize speech
    base64_audio = await synthesize_speech(transcription, voice_code)

    if base64_audio:
        # Lock microphones during audio playback
        speaking_status[room_code]['isSynthesizedAudioPlaying'] = True
        await sio.emit('lockMicrophone', {'isSpeaking': False, 'isSynthesizedAudioPlaying': True}, room=room_code)

        # Send the synthesized audio to the room
        await sio.emit('synthesizedAudio', {'audio': base64_audio}, room=room_code)

        # Once audio has played, unlock microphones
        speaking_status[room_code]['isSynthesizedAudioPlaying'] = False
        await sio.emit('lockMicrophone', {'isSpeaking': False, 'isSynthesizedAudioPlaying': False}, room=room_code)

# Handle when someone starts speaking
@sio.event
async def startSpeaking(sid, data):
    room_code = data.get('roomCode')

    if not room_code:
        return

    speaking_status[room_code]['isSpeaking'] = True
    await sio.emit('lockMicrophone', {'isSpeaking': True, 'isSynthesizedAudioPlaying': False}, room=room_code)

# Handle when someone stops speaking
@sio.event
async def stopSpeaking(sid, data):
    room_code = data.get('roomCode')

    if not room_code:
        return

    speaking_status[room_code]['isSpeaking'] = False
    await sio.emit('lockMicrophone', {'isSpeaking': False, 'isSynthesizedAudioPlaying': False}, room=room_code)


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
