from pydantic import BaseModel

class Avatar(BaseModel):
    # avatar_id: int
    avatar_name: str
    avatar_img: str
    voice_code: str
