from fastapi import APIRouter, HTTPException
from models.avatar import Avatar
from typing import List
from db import get_db_connection

router = APIRouter()

@router.get("/", response_model=List[Avatar])
async def fetch_avatars():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM tbl_aiterp_Avatars"
            cursor.execute(query)
            rows = cursor.fetchall()
            #avatars = [Avatar(avatar_id=row[0], avatar_name=row[1], avatar_img=row[2], voice_code=row[3]) for row in rows]
            avatars = rows
            return avatars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/", response_model=Avatar)
async def create_avatar(avatar: Avatar):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO tbl_aiterp_Avatars ( avatar_name, avatar_img, voice_code)
                VALUES ( ?, ?, ?)
            """
            cursor.execute(query,  avatar.avatar_name, avatar.avatar_img, avatar.voice_code)
            conn.commit()
            return avatar
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
