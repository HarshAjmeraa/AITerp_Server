from pydantic import BaseModel
from datetime import datetime

class Attendee(BaseModel):
    user_name: str
    session_id: str
    join_time : datetime
    designation : str
