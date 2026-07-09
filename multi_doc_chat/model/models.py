from datetime import datetime
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, EmailStr

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


class DocumentResponse(BaseModel):
    filename: str
    file_type: str
    file_path: str
    faiss_index_path: Optional[str] = None
    pageindex_doc_id: Optional[str] = None
    created_at: datetime


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionSummaryResponse(BaseModel):
    session_id: str
    display_name: str
    created_at: datetime
    document_count: int
    message_count: int
    backend: Optional[str] = None
    is_active: bool


class RenameSessionRequest(BaseModel):
    display_name: Annotated[str, Field(min_length=1, max_length=255)]


class RenameSessionResponse(BaseModel):
    session_id: str
    display_name: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
