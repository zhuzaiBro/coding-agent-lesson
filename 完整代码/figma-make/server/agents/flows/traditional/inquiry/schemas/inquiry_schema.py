"""Database inquiry (QA + live DB) structured steps."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InquiryAction(str, Enum):
    QUERY = "query"
    ANSWER = "answer"


class InquiryStep(BaseModel):
    action: InquiryAction = Field(
        description="query: run a read-only SQL; answer: return final reply to user",
    )
    sql: Optional[str] = Field(
        default=None,
        description="PostgreSQL SELECT/WITH when action=query",
    )
    message: str = Field(
        description="When query: why this SQL; when answer: final user-facing reply in Chinese",
    )
