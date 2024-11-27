from fastapi import APIRouter, HTTPException
from models.avatar import Avatar, AvatarResponse
from typing import List
from db import get_db_connection

router = APIRouter()

@router.get("/fetch/{language_id}", response_model=List[AvatarResponse])
async def fetch_avatars(language_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch avatars filtered by language_id
            cursor.execute("SELECT avatar_id, avatar_name, avatar_img, rate_per_min FROM tbl_aiterp_Avatars WHERE language_id = ?", (language_id,))
            avatars = cursor.fetchall()
            
            if avatars:
                # Map results to the Avatar model
                result = [{"avatar_id": avatar[0], "avatar_name": avatar[1], "avatar_img": avatar[2], "rate_per_min": avatar[3]} for avatar in avatars]
                return result
            else:
                raise HTTPException(status_code=404, detail=f"No avatars found for language_id {language_id}")

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
