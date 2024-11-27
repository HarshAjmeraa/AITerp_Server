from fastapi import APIRouter, HTTPException
from models.attendee import Attendee
from typing import List
from db import get_db_connection

router = APIRouter()

def get_next_user_id(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(user_id AS INT)) FROM tbl_aiterp_Attendee")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return '0000'
    next_id = int(max_id) + 1
    return f'{next_id:04d}'

@router.post("/", response_model=List[Attendee])
async def add_attendees(attendees: List[Attendee]):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO tbl_aiterp_Attendee (user_name, session_id, join_time, designation)
                VALUES (?, ?, ?, ?)
            """
            for attendee in attendees:
                cursor.execute(query, (attendee.user_name, attendee.session_id, attendee.join_time, attendee.designation))
            conn.commit()
            return attendees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
