from pydantic import BaseModel

class Avatar(BaseModel):
    # avatar_id: int
    avatar_name: str
    avatar_img: str
    voice_code: str

class AvatarResponse(BaseModel):
    avatar_id: int
    avatar_name: str
    avatar_img: str
    rate_per_min: float
