"""step0: Behavior analysis schema."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    QA = "QA"
    CHIT_CHAT = "CHIT_CHAT"


class Complexity(str, Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class AnalysisResult(BaseModel):
    type: IntentType = Field(description="User intent type: create new app, modify existing, Q&A, or chit-chat")
    summary: str = Field(description="Brief summary of user requirements")
    tags: List[str] = Field(description="Related technical tags or keywords")
    complexity: Complexity = Field(description="Estimated task complexity")
    needsDatabase: bool = Field(
        description=(
            "Whether answering or fulfilling this request requires connecting to a live "
            "database (query/update real rows, verify data pipelines, persist user data, auth, etc.). "
            "True for data investigation, CRUD backends, login/signup, order/payment traces; "
            "False for pure UI mockups, static pages, chit-chat, or theoretical explanations."
        ),
    )
    databaseReason: Optional[str] = Field(
        default=None,
        description="When needsDatabase is true, one sentence explaining why DB access is required.",
    )
    designAnalysis: Optional[str] = Field(
        default=None,
        description="If user mentions design requirements (e.g. 'beautiful UI', 'modern style'), briefly describe design intent; otherwise null.",
    )
