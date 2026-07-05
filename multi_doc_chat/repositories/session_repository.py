from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.db import models


def build_session(
    session_id: str,
    user_id: Optional[int] = None,
) -> models.Session:
    return models.Session(session_id=session_id, user_id=user_id)


def add_session(
    db: DBSession,
    session: models.Session,
) -> models.Session:
    db.add(session)
    return session


def get_session_by_session_id(
    db: DBSession,
    session_id: str,
) -> Optional[models.Session]:
    return (
        db.query(models.Session)
        .filter(models.Session.session_id == session_id)
        .first()
    )


def build_document(
    session_pk: int,
    filename: str,
    file_path: str,
    file_type: str,
    faiss_index_path: Optional[str] = None,
    pageindex_doc_id: Optional[str] = None,
) -> models.Document:
    return models.Document(
        session_id=session_pk,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        faiss_index_path=faiss_index_path,
        pageindex_doc_id=pageindex_doc_id,
    )


def add_document(
    db: DBSession,
    document: models.Document,
) -> models.Document:
    db.add(document)
    return document


def get_documents_for_session(
    db: DBSession,
    session_pk: int,
) -> List[models.Document]:
    """
    Return all documents belonging to a given session.
    Used by the service layer to derive PageIndex doc_ids from Postgres.
    """
    return (
        db.query(models.Document)
        .filter(models.Document.session_id == session_pk)
        .all()
    )


def build_chat_message(
    session_pk: int,
    role: str,
    content: str,
) -> models.ChatMessage:
    return models.ChatMessage(
        session_id=session_pk,
        role=role,
        content=content,
    )


def add_chat_message(
    db: DBSession,
    message: models.ChatMessage,
) -> models.ChatMessage:
    db.add(message)
    return message


def get_chat_history(
    db: DBSession,
    session_pk: int,
) -> List[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_pk)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )