from __future__ import annotations

from typing import List, Optional

from sqlalchemy import case, func
from multi_doc_chat.db import models
from sqlalchemy.orm import Session as DBSession, selectinload

def build_session(
    session_id: str,
    user_id: Optional[int] = None,
) -> models.Session:
    return models.Session(
        session_id=session_id,
        user_id=user_id,
    )


def add_session(
    db: DBSession,
    session: models.Session,
) -> models.Session:
    db.add(session)
    return session


# def get_session_by_session_id(
#     db: DBSession,
#     session_id: str,
# ) -> Optional[models.Session]:
#     return (
#         db.query(models.Session)
#         .filter(models.Session.session_id == session_id)
#         .first()
#     )

def get_session_by_session_id(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> Optional[models.Session]:
    query = (
        db.query(models.Session)
        .filter(models.Session.session_id == session_id)
    )

    if user_id is not None:
        query = query.filter(models.Session.user_id == user_id)

    return query.first()
#------------------------------------------------
# def get_session_by_session_id_with_documents(
#     db: DBSession,
#     session_id: str,
# ) -> Optional[models.Session]:
#     return (
#         db.query(models.Session)
#         .options(selectinload(models.Session.documents))
#         .filter(models.Session.session_id == session_id)
#         .first()
#     )

def get_session_by_session_id_with_documents(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> Optional[models.Session]:
    query = (
        db.query(models.Session)
        .options(selectinload(models.Session.documents))
        .filter(models.Session.session_id == session_id)
    )

    if user_id is not None:
        query = query.filter(models.Session.user_id == user_id)

    return query.first()


def get_all_sessions_with_counts(
    db: DBSession,
    *,
    user_id: Optional[int] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    doc_counts = (
        db.query(
            models.Document.session_id.label("session_pk"),
            func.count(models.Document.id).label("document_count"),
        )
        .group_by(models.Document.session_id)
        .subquery()
    )

    msg_counts = (
        db.query(
            models.ChatMessage.session_id.label("session_pk"),
            func.count(models.ChatMessage.id).label("message_count"),
        )
        .group_by(models.ChatMessage.session_id)
        .subquery()
    )

    pageindex_flags = (
        db.query(
            models.Document.session_id.label("session_pk"),
            func.max(
                case(
                    (models.Document.pageindex_doc_id.is_not(None), 1),
                    else_=0,
                )
            ).label("has_pageindex"),
            func.max(
                case(
                    (models.Document.faiss_index_path.is_not(None), 1),
                    else_=0,
                )
            ).label("has_faiss"),
        )
        .group_by(models.Document.session_id)
        .subquery()
    )

    query = (
        db.query(
            models.Session.session_id,
            models.Session.created_at,
            models.Session.is_active,
            func.coalesce(doc_counts.c.document_count, 0).label("document_count"),
            func.coalesce(msg_counts.c.message_count, 0).label("message_count"),
            func.coalesce(pageindex_flags.c.has_pageindex, 0).label("has_pageindex"),
            func.coalesce(pageindex_flags.c.has_faiss, 0).label("has_faiss"),
        )
        .outerjoin(doc_counts, doc_counts.c.session_pk == models.Session.id)
        .outerjoin(msg_counts, msg_counts.c.session_pk == models.Session.id)
        .outerjoin(pageindex_flags, pageindex_flags.c.session_pk == models.Session.id)
        .order_by(models.Session.created_at.desc())
    )

    if user_id is not None:
        query = query.filter(models.Session.user_id == user_id)

    if not include_inactive:
        query = query.filter(models.Session.is_active.is_(True))

    return query.offset(offset).limit(limit).all()


def get_session_documents(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> List[models.Document]:
    query = (
        db.query(models.Document)
        .join(models.Session, models.Document.session_id == models.Session.id)
        .filter(models.Session.session_id == session_id)
        .order_by(models.Document.created_at.asc())
    )

    if user_id is not None:
        query = query.filter(models.Session.user_id == user_id)

    return query.all()


def get_session_messages(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> List[models.ChatMessage]:
    query = (
        db.query(models.ChatMessage)
        .join(models.Session, models.ChatMessage.session_id == models.Session.id)
        .filter(models.Session.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
    )

    if user_id is not None:
        query = query.filter(models.Session.user_id == user_id)

    return query.all()


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


def delete_session(
    db: DBSession,
    session_obj: models.Session,
) -> None:
    db.delete(session_obj)


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
