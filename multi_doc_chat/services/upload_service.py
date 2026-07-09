# from __future__ import annotations
# import shutil
# from pathlib import Path
# from typing import List
# from sqlalchemy.orm import Session as DBSession

# from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
# from multi_doc_chat.utils.document_ops import FastAPIFileAdapter
# from multi_doc_chat.utils.config_loader import load_config
# from multi_doc_chat.services.session_service import DocumentInput, create_session_with_documents
# from multi_doc_chat.exception.custom_exception import DocumentPortalException
# from multi_doc_chat.logger.custom_logger import CustomLogger

# log = CustomLogger().get_logger(__name__)


# class UploadService:
#     def __init__(self, db: DBSession):
#         self.db = db
#         self.cfg = load_config()

#     def _cleanup_dirs(self, temp_dir: Path, faiss_dir: Path) -> None:
#         # Compensating transaction: clean up filesystem on failure
#         for d in {temp_dir, faiss_dir}:
#             try:
#                 if d.exists():
#                     shutil.rmtree(d)
#                     log.info("Cleaned directory after upload failure", dir=str(d))
#             except Exception as e:
#                 # Log, but do not mask the original upload error
#                 log.warning("Failed to cleanup directory", dir=str(d), error=str(e))

#     def process_upload(
#         self,
#         wrapped_files: List[FastAPIFileAdapter],
#         original_filenames: List[str],
#     ) -> str:
#         """
#         Orchestrates the full upload pipeline:

#         - Save files
#         - Build retriever (FAISS or PageIndex)
#         - Insert session + documents into DB
#         - Commit ONCE

#         If anything fails:
#         - Rollback DB
#         - Remove temp_dir and faiss_dir
#         - Raise DocumentPortalException
#         """
#         retrieval_cfg = self.cfg.get("retrieval", {})
#         mode = retrieval_cfg.get("mode", "mmr")

#         ingestor = ChatIngestor(use_session_dirs=True)
#         session_id = ingestor.session_id

#         temp_dir = ingestor.temp_dir
#         faiss_dir = ingestor.faiss_dir

#         try:
#             # 1) Save files + build retriever
#             if mode in ("similarity", "mmr"):
#                 ingestor.built_retriever(
#                     uploaded_files=wrapped_files,
#                     search_type=mode,
#                     k=retrieval_cfg.get("top_k", 5),
#                 )
#             elif mode == "pageindex":
#                 non_pdf = [name for name in original_filenames if not name.lower().endswith(".pdf")]
#                 if non_pdf:
#                     raise DocumentPortalException(
#                         "PageIndex mode only supports PDF files",
#                         f"Unsupported files: {', '.join(non_pdf)}",
#                     )
#                 ingestor.built_retriever(
#                     uploaded_files=wrapped_files,
#                     search_type="pageindex",
#                 )
#             else:
#                 raise DocumentPortalException(
#                     "Unsupported retrieval mode",
#                     f"Mode '{mode}' is not recognized.",
#                 )

#             # 2) Build document DTOs for DB
#             document_inputs: List[DocumentInput] = []
#             for name in original_filenames:
#                 file_type = Path(name).suffix.lstrip(".").lower()
#                 file_path = str(temp_dir / name)
#                 document_inputs.append(
#                     DocumentInput(
#                         filename=name,
#                         file_path=file_path,
#                         file_type=file_type,
#                         faiss_index_path=str(faiss_dir) if mode in ("similarity", "mmr") else None,
#                         pageindex_doc_id=None,  # wire your doc_ids here if you expose them
#                     )
#                 )

#             # 3) Persist session + documents in ONE transaction
#             create_session_with_documents(
#                 db=self.db,
#                 session_id=session_id,
#                 documents=document_inputs,
#             )

#             # If we reach here, DB commit has already happened inside create_session_with_documents
#             return session_id

#         except Exception as e:
#             # Compensating transaction: rollback + cleanup
#             self.db.rollback()  # extra safety, in case inner service didn't reach commit
#             self._cleanup_dirs(temp_dir, faiss_dir)
#             log.error("Upload pipeline failed", session_id=session_id, error=str(e))
#             if isinstance(e, DocumentPortalException):
#                 raise
#             raise DocumentPortalException("Upload pipeline failed", str(e)) from e



# multi_doc_chat/services/upload_service.py

from __future__ import annotations
import shutil
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.utils.document_ops import FastAPIFileAdapter
from multi_doc_chat.services.session_service import DocumentInput, create_session_with_documents
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger.custom_logger import CustomLogger

log = CustomLogger().get_logger(__name__)


class UploadService:
    def __init__(self, db: DBSession, cfg: dict):
        self.db = db
        self.cfg = cfg

    def _resolve_retrieval_mode(self, retrieval_backend: str | None) -> str:
        config_mode = self.cfg.get("retrieval", {}).get("mode", "mmr")

        if retrieval_backend:
            normalized = retrieval_backend.strip().lower()
            if normalized in ("similarity", "mmr", "pageindex"):
                return normalized
            if normalized == "faiss":
                if config_mode in ("similarity", "mmr"):
                    return config_mode
                return "mmr"

        return config_mode

    def _cleanup_dirs(self, temp_dir: Path, faiss_dir: Path) -> None:
        for d in {temp_dir, faiss_dir}:
            try:
                if d.exists():
                    shutil.rmtree(d)
                    log.info("Cleaned directory after upload failure", dir=str(d))
            except Exception as e:
                log.warning("Failed to cleanup directory", dir=str(d), error=str(e))

    def process_upload(
        self,
        wrapped_files: List[FastAPIFileAdapter],
        original_filenames: List[str],
        user_id: int,
        retrieval_backend: str | None = None,
    ) -> str:
        retrieval_cfg = self.cfg.get("retrieval", {})
        mode = self._resolve_retrieval_mode(retrieval_backend)

        ingestor = ChatIngestor(use_session_dirs=True, cfg=self.cfg)
        session_id = ingestor.session_id

        temp_dir = ingestor.temp_dir
        faiss_dir = ingestor.faiss_dir

        try:
            pageindex_doc_ids: List[str] = []

            # 1) Save files and build backend
            if mode in ("similarity", "mmr"):
                ingestor.built_retriever(
                    uploaded_files=wrapped_files,
                    search_type=mode,
                    k=retrieval_cfg.get("top_k", 5),
                )
            elif mode == "pageindex":
                non_pdf = [name for name in original_filenames if not name.lower().endswith(".pdf")]
                if non_pdf:
                    raise DocumentPortalException(
                        "PageIndex mode only supports PDF files",
                        f"Unsupported files: {', '.join(non_pdf)}",
                    )

                # built_retriever returns List[str] of PageIndex doc_ids for PDFs
                pageindex_doc_ids = ingestor.built_retriever(
                    uploaded_files=wrapped_files,
                    search_type="pageindex",
                )
            else:
                raise DocumentPortalException(
                    "Unsupported retrieval mode",
                    f"Mode '{mode}' is not recognized.",
                )

            # 2) Build document inputs
            document_inputs: List[DocumentInput] = []

            if mode in ("similarity", "mmr"):
                for name in original_filenames:
                    file_type = Path(name).suffix.lstrip(".").lower()
                    file_path = str(temp_dir / name)
                    document_inputs.append(
                        DocumentInput(
                            filename=name,
                            file_path=file_path,
                            file_type=file_type,
                            faiss_index_path=str(faiss_dir),
                            pageindex_doc_id=None,
                        )
                    )

            elif mode == "pageindex":
                pdf_names = [name for name in original_filenames if name.lower().endswith(".pdf")]

                if len(pageindex_doc_ids) != len(pdf_names):
                    log.warning(
                        "Mismatch between PageIndex doc_ids and PDF filenames",
                        session_id=session_id,
                        doc_id_count=len(pageindex_doc_ids),
                        pdf_count=len(pdf_names),
                    )

                # Correct mapping: nth PDF → nth doc_id, using a separate counter
                pdf_idx = 0
                for name in original_filenames:
                    file_type = Path(name).suffix.lstrip(".").lower()
                    file_path = str(temp_dir / name)

                    pageindex_doc_id = None
                    if name.lower().endswith(".pdf"):
                        if pdf_idx < len(pageindex_doc_ids):
                            pageindex_doc_id = pageindex_doc_ids[pdf_idx]
                        pdf_idx += 1

                    document_inputs.append(
                        DocumentInput(
                            filename=name,
                            file_path=file_path,
                            file_type=file_type,
                            faiss_index_path=None,
                            pageindex_doc_id=pageindex_doc_id,
                        )
                    )

            # 3) Attach session + documents, then commit once
            create_session_with_documents(
                db=self.db,
                session_id=session_id,
                documents=document_inputs,
                display_name=session_id,
                user_id=user_id,
            )

            self.db.commit()
            log.info("Upload pipeline committed", session_id=session_id)
            return session_id

        except Exception as e:
            self.db.rollback()
            self._cleanup_dirs(temp_dir, faiss_dir)
            log.error("Upload pipeline failed", session_id=session_id, error=str(e))
            if isinstance(e, DocumentPortalException):
                raise
            raise DocumentPortalException("Upload pipeline failed", str(e)) from e
