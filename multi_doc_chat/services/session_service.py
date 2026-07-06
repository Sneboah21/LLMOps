from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.db import models
from multi_doc_chat.repositories import session_repository as repo
from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)


class DocumentInput:
    """Simple DTO describing a document to persist alongside a session."""

    __slots__ = (
        "filename",
        "file_path",
        "file_type",
        "faiss_index_path",
        "pageindex_doc_id",
    )

    def __init__(
        self,
        filename: str,
        file_path: str,
        file_type: str,
        faiss_index_path: Optional[str] = None,
        pageindex_doc_id: Optional[str] = None,
    ):
        self.filename = filename
        self.file_path = file_path
        self.file_type = file_type
        self.faiss_index_path = faiss_index_path
        self.pageindex_doc_id = pageindex_doc_id


def create_session_with_documents(
    db: DBSession,
    session_id: str,
    documents: List[DocumentInput],
    user_id: Optional[int] = None,
) -> models.Session:
    """
    Build a session row and all associated document rows.

    This function:
      - Adds objects to the SQLAlchemy session.
      - Flushes to populate session_obj.id.
    It does NOT commit or roll back; the caller owns the transaction boundary.
    """
    try:
        session_obj = repo.build_session(
            session_id=session_id,
            user_id=user_id,
        )
        repo.add_session(db, session_obj)

        # Flush to get session_obj.id populated without committing yet
        db.flush()

        for doc_input in documents:
            document = repo.build_document(
                session_pk=session_obj.id,
                filename=doc_input.filename,
                file_path=doc_input.file_path,
                file_type=doc_input.file_type,
                faiss_index_path=doc_input.faiss_index_path,
                pageindex_doc_id=doc_input.pageindex_doc_id,
            )
            repo.add_document(db, document)

        # Refresh so any DB-populated fields on session_obj are available
        db.refresh(session_obj)

        log.info(
            "Session and documents persisted (pending commit by caller)",
            session_id=session_id,
            document_count=len(documents),
        )
        return session_obj

    except Exception as e:
        log.error(
            "Failed to persist session and documents",
            session_id=session_id,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to persist session and documents", str(e)
        ) from e


# def get_session_by_session_id(
#     db: DBSession,
#     session_id: str,
# ) -> Optional[models.Session]:
#     return repo.get_session_by_session_id(db, session_id)

def get_session_by_session_id(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> Optional[models.Session]:
    return repo.get_session_by_session_id(
        db,
        session_id,
        user_id=user_id,
    )

def get_chat_history(
    db: DBSession,
    session_pk: int,
) -> List[models.ChatMessage]:
    return repo.get_chat_history(db, session_pk)


def record_chat_turn(
    db: DBSession,
    session_pk: int,
    user_message: str,
    assistant_message: str,
) -> None:
    """
    Attach both the user message and assistant response
    for a single chat turn to the current DB session.

    The caller is responsible for committing or rolling back.
    """
    try:
        user_msg = repo.build_chat_message(
            session_pk=session_pk,
            role="user",
            content=user_message,
        )
        repo.add_chat_message(db, user_msg)

        assistant_msg = repo.build_chat_message(
            session_pk=session_pk,
            role="assistant",
            content=assistant_message,
        )
        repo.add_chat_message(db, assistant_msg)

        log.info(
            "Chat turn persisted (pending commit by caller)",
            session_pk=session_pk,
        )

    except Exception as e:
        log.error(
            "Failed to persist chat turn",
            session_pk=session_pk,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to persist chat turn", str(e)
        ) from e


def get_pageindex_doc_ids_for_session(
    db: DBSession,
    session_pk: int,
) -> List[str]:
    """
    Return all non-null PageIndex doc_ids for a given session
    from the documents table.

    This is used by the /chat endpoint in PageIndex mode to know
    which PageIndex documents to search.
    """
    try:
        docs: List[models.Document] = repo.get_documents_for_session(
            db, session_pk
        )
        doc_ids = [
            d.pageindex_doc_id
            for d in docs
            if getattr(d, "pageindex_doc_id", None)
        ]

        log.info(
            "Loaded PageIndex doc_ids for session",
            session_pk=session_pk,
            doc_id_count=len(doc_ids),
        )
        return doc_ids

    except Exception as e:
        log.error(
            "Failed to load PageIndex doc_ids for session",
            session_pk=session_pk,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to load PageIndex document ids for session", str(e)
        ) from e


def list_sessions(
    db: DBSession,
    *,
    user_id: Optional[int] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    try:
        rows = repo.get_all_sessions_with_counts(
            db,
            user_id=user_id,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )

        summaries: List[Dict[str, Any]] = []
        for row in rows:
            backend = None
            if row.has_pageindex:
                backend = "pageindex"
            elif row.has_faiss:
                backend = "faiss"

            summaries.append(
                {
                    "session_id": row.session_id,
                    "created_at": row.created_at,
                    "document_count": row.document_count,
                    "message_count": row.message_count,
                    "backend": backend,
                    "is_active": row.is_active,
                }
            )

        log.info(
            "Session summaries loaded",
            count=len(summaries),
            user_id=user_id,
            include_inactive=include_inactive,
        )
        return summaries

    except Exception as e:
        log.error(
            "Failed to list sessions",
            user_id=user_id,
            include_inactive=include_inactive,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to list sessions",
            str(e),
        ) from e


def get_session_documents(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> List[models.Document]:
    try:
        docs = repo.get_session_documents(
            db,
            session_id=session_id,
            user_id=user_id,
        )

        log.info(
            "Session documents loaded",
            session_id=session_id,
            document_count=len(docs),
        )
        return docs

    except Exception as e:
        log.error(
            "Failed to load session documents",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to load session documents",
            str(e),
        ) from e


def get_session_messages(
    db: DBSession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> List[models.ChatMessage]:
    try:
        messages = repo.get_session_messages(
            db,
            session_id=session_id,
            user_id=user_id,
        )

        log.info(
            "Session messages loaded",
            session_id=session_id,
            message_count=len(messages),
        )
        return messages

    except Exception as e:
        log.error(
            "Failed to load session messages",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
        )
        raise DocumentPortalException(
            "Failed to load session messages",
            str(e),
        ) from e
