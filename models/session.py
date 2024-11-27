from pydantic import BaseModel

class SessionRequest(BaseModel):
    session_id: str
    job_id: str
    avatar_id: int
