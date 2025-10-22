from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class inputPrompt(BaseModel):
    user_id: UUID
    input_prompt: str