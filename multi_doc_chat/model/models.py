from enum import Enum
from pydantic import BaseModel, Field
from  typing import Annotated

class PromptType(str, Enum):
    """
    Prompt registry keys used throughout the RAG system.
    """
    CONTEXTUALIZE_QUESTION = "contextualize_question"
    CONTEXT_QA = "context_qa"


class ChatAnswer(BaseModel):
    """
    Validates chat answer type and length.
    """
    answer: Annotated[str, Field(min_length=1, max_length=4096)]  #Example constraints

#Pydantic models
class UploadResponse(BaseModel):
    session_id: str
    indexed: bool
    message: str | None = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
    