from pydantic import BaseModel

class SessionRequest(BaseModel):
    job_id: str
    avatar_id: int
