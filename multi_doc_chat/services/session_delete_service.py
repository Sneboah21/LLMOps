from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.db import models
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.repositories import session_repository as repo
from multi_doc_chat.src.document_chat.pageindex_retriever import (
    delete_pageindex_document,
    get_pageindex_client,
)

log = CustomLogger().get_logger(__name__)


class SessionNotFoundError(DocumentPortalException):
    pass


class ExternalCleanupError(DocumentPortalException):
    pass


@dataclass
class SessionDeleteResult:
    session_id: str
    deleted_document_rows: int = 0
    deleted_pageindex_docs: int = 0
    deleted_files: int = 0
    deleted_faiss_dirs: int = 0
    warnings: List[str] = field(default_factory=list)


class SessionDeletionService:
    """
    Orchestrates complete session deletion.

    External resources are deleted first.
    Database deletion is committed once at the end.

    If DB deletion fails after external cleanup succeeds,
    retrying the delete request is safe because external deletions
    are treated idempotently where possible.
    """

    def __init__(self, db: DBSession, cfg: dict):
        self.db = db
        self.cfg = cfg

    def delete_session(self, session_id: str, *, user_id: int) -> SessionDeleteResult:
        try:
            session_obj = repo.get_session_by_session_id_with_documents(
                self.db,
                session_id,
                user_id=user_id,
            )

            if session_obj is None:
                raise SessionNotFoundError(
                    f"Session '{session_id}' not found."
                )

            documents = list(session_obj.documents or [])
            result = SessionDeleteResult(
                session_id=session_id,
                deleted_document_rows=len(documents),
            )

            pageindex_doc_ids = [
                doc.pageindex_doc_id
                for doc in documents
                if getattr(doc, "pageindex_doc_id", None)
            ]

            unique_faiss_dirs: Set[str] = {
                doc.faiss_index_path
                for doc in documents
                if getattr(doc, "faiss_index_path", None)
            }

            client = None
            if pageindex_doc_ids:
                client = get_pageindex_client(self.cfg)

            external_errors: List[str] = []

            # 1) Delete PageIndex documents
            if client is not None:
                for doc in documents:
                    doc_id = getattr(doc, "pageindex_doc_id", None)
                    if not doc_id:
                        continue

                    try:
                        deleted = delete_pageindex_document(doc_id, client)
                        if deleted:
                            result.deleted_pageindex_docs += 1
                        else:
                            result.warnings.append(
                                f"PageIndex document already missing: {doc_id}"
                            )
                    except Exception as e:
                        external_errors.append(
                            f"PageIndex delete failed for doc_id={doc_id}: {str(e)}"
                        )

            # 2) Delete uploaded files
            for doc in documents:
                file_path = getattr(doc, "file_path", None)
                if not file_path:
                    continue

                try:
                    deleted = self._delete_file_if_exists(file_path)
                    if deleted:
                        result.deleted_files += 1
                    else:
                        result.warnings.append(
                            f"Uploaded file already missing: {file_path}"
                        )
                except Exception as e:
                    external_errors.append(
                        f"File delete failed for path={file_path}: {str(e)}"
                    )

            # 3) Delete FAISS directories once
            for faiss_dir in unique_faiss_dirs:
                try:
                    deleted = self._delete_dir_if_exists(faiss_dir)
                    if deleted:
                        result.deleted_faiss_dirs += 1
                    else:
                        result.warnings.append(
                            f"FAISS directory already missing: {faiss_dir}"
                        )
                except Exception as e:
                    external_errors.append(
                        f"FAISS dir delete failed for path={faiss_dir}: {str(e)}"
                    )

            # Abort before DB delete if any external cleanup failed
            if external_errors:
                self.db.rollback()

                log.error(
                    "Session deletion aborted due to external cleanup failure",
                    session_id=session_id,
                    errors=external_errors,
                )

                raise ExternalCleanupError(
                    "Session deletion aborted because external cleanup failed: "
                    + " | ".join(external_errors)
                )

            # 4) Delete DB session row (cascades to documents + chat_messages)
            repo.delete_session(self.db, session_obj)

            # Optional flush before commit for earlier DB error detection
            self.db.flush()
            self.db.commit()

            log.info(
                "Session deleted successfully",
                session_id=session_id,
                deleted_document_rows=result.deleted_document_rows,
                deleted_pageindex_docs=result.deleted_pageindex_docs,
                deleted_files=result.deleted_files,
                deleted_faiss_dirs=result.deleted_faiss_dirs,
                warnings=result.warnings,
            )

            return result

        except DocumentPortalException:
            raise

        except Exception as e:
            self.db.rollback()

            log.error(
                "Session deletion failed",
                session_id=session_id,
                error=str(e),
            )

            raise DocumentPortalException(
                "Failed to delete session",
                e,
            ) from e

    def _delete_file_if_exists(self, file_path: str) -> bool:
        path = Path(file_path)

        if not path.exists():
            return False

        if not path.is_file():
            raise RuntimeError(f"Expected file but found non-file path: {file_path}")

        path.unlink()

        log.info(
            "Uploaded file deleted",
            file_path=file_path,
        )
        return True

    def _delete_dir_if_exists(self, dir_path: str) -> bool:
        path = Path(dir_path)

        if not path.exists():
            return False

        if not path.is_dir():
            raise RuntimeError(f"Expected directory but found non-directory path: {dir_path}")

        shutil.rmtree(path)

        log.info(
            "FAISS directory deleted",
            dir_path=dir_path,
        )
        return True