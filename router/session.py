from fastapi import APIRouter, HTTPException
from models.session import SessionRequest
from db import get_db_connection, pyodbc
import random
import string

router = APIRouter()

# def generate_unique_session_id(cursor) -> str:
#     while True:
#         session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
#         cursor.execute("SELECT COUNT(*) FROM tbl_aiterp_Sessions WHERE session_id = ?", session_id)
#         count = cursor.fetchone()[0]
#         if count == 0:
#             return session_id

# @router.post("/create_session")
# async def create_session(session_request: SessionRequest):
#     try:
#         with get_db_connection() as conn:
#             cursor = conn.cursor()
#             session_id = generate_unique_session_id(cursor)

#             query = """
#                 INSERT INTO tbl_aiterp_Sessions (session_id, job_id, avatar_id)
#                 VALUES (?, ?, ?)
#             """
#             cursor.execute(query, session_id, session_request.job_id, session_request.avatar_id)
#             conn.commit()
#             return {"session_id": session_id}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.post("/add_session")
async def add_session(session_request: SessionRequest):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Insert the session data directly using the values from the request
            query = """
                INSERT INTO tbl_aiterp_Sessions (session_id, job_id, avatar_id)
                VALUES (?, ?, ?)
            """
            cursor.execute(query, session_request.session_id, session_request.job_id, session_request.avatar_id)
            conn.commit()
            
            # Return the session ID as confirmation
            return {"session_id": session_request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get("/validate_session/{session_id}")
async def validate_session(session_id: str):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job_id, avatar_id FROM tbl_aiterp_Sessions WHERE session_id = ?", session_id)
            result = cursor.fetchone()
            if result:
                job_id = result[0]
                avatar_id = result[1]

                cursor.execute("SELECT avatar_id, avatar_name, avatar_img, voice_code FROM tbl_aiterp_Avatars WHERE avatar_id = ?", avatar_id)
                avatar_details = cursor.fetchone()
                if avatar_details:
                    avatar = {
                        "avatar_id": avatar_details[0],
                        "avatar_name": avatar_details[1],
                        "avatar_img": avatar_details[2],
                        "voice_code": avatar_details[3]
                    }
                    return {"detail": "Session ID is valid", "job_id": job_id, "avatar": avatar}
                else:
                    return {"detail": "Session ID is valid, but avatar details not found"}
            else:
                return {"detail": "Session ID is invalid"}  # Modified this line
    except pyodbc.OperationalError as e:
        if "IP address" in str(e):
            raise HTTPException(status_code=503, detail="Unable to connect to database due to IP address error")
        else:
            raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
    except pyodbc.ProgrammingError as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
