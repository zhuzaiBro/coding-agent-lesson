"""Simple conversational reply schema."""
from pydantic import BaseModel, Field


class ChatReplyResult(BaseModel):
    message: str = Field(description="User-facing reply in Chinese")
