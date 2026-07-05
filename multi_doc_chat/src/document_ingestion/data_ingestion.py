from __future__ import annotations
import hashlib
from pathlib import Path
import sys
from typing import Iterable, List, Optional, Dict, Any, Union
import uuid
from datetime import datetime
import json

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.utils.file_io import save_uploaded_files
from multi_doc_chat.utils.model_loader import ModelLoader
from multi_doc_chat.utils.document_ops import load_documents
from multi_doc_chat.utils.config_loader import load_config

from multi_doc_chat.src.document_chat.pageindex_retriever import (
    get_pageindex_client,
    submit_document,
)

log = CustomLogger().get_logger(__name__)


def generate_session_id() -> str:
    """Generate a unique session ID with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"session_{timestamp}_{unique_id}"


class ChatIngestor:
    def __init__(
        self,
        temp_base: str = "data",
        faiss_base: str = "faiss_index",
        use_session_dirs: bool = True,
        session_id: Optional[str] = None,
        cfg: Optional[dict] = None,
    ):
        try:
            self.model_loader = ModelLoader()
            self.cfg = cfg or load_config()
            self.use_session = use_session_dirs
            self.session_id = session_id or generate_session_id()

            self.temp_base = Path(temp_base)
            self.temp_base.mkdir(parents=True, exist_ok=True)

            self.faiss_base = Path(faiss_base)
            self.faiss_base.mkdir(parents=True, exist_ok=True)

            self.temp_dir = self._resolve_dir(self.temp_base)
            self.faiss_dir = self._resolve_dir(self.faiss_base)

            log.info(
                "ChatIngestor initialized",
                session_id=self.session_id,
                temp_dir=str(self.temp_dir),
                faiss_dir=str(self.faiss_dir),
                sessionlized=self.use_session,
            )

        except Exception as e:
            log.error("Failed to initialize ChatIngestor", error=str(e))
            raise DocumentPortalException("Initialization error in ChatIngestor", e) from e

    def _resolve_dir(self, base: Path) -> Path:
        if self.use_session:
            d = base / self.session_id
            d.mkdir(parents=True, exist_ok=True)
            return d
        return base

    def _split(self, docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(docs)
        log.info(
            "Documents split",
            chunks=len(chunks),
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )
        return chunks

    def built_retriever(
        self,
        uploaded_files: Iterable,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        k: int = 5,
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> Union[BaseRetriever, List[str]]:
        """
        Prepare retrieval backend for this session.

        - For "similarity" / "mmr":
            * Ingest docs into FAISS
            * Return a LangChain retriever

        - For "pageindex":
            * Save files
            * Upload PDFs to PageIndex
            * Return list of doc_ids for this session
        """
        try:
            paths = save_uploaded_files(uploaded_files, self.temp_dir)

            if search_type in ("similarity", "mmr"):
                log.info(
                    "Starting FAISS ingestion pipeline",
                    session_id=self.session_id,
                    file_count=len(paths),
                    search_type=search_type,
                )

                docs = load_documents(paths)
                if not docs:
                    raise DocumentPortalException("No valid documents loaded for FAISS ingestion.")

                chunks = self._split(
                    docs,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                if not chunks:
                    raise DocumentPortalException("Document loading succeeded but no chunks were produced.")

                texts = [c.page_content for c in chunks]
                metas = [c.metadata for c in chunks]

                log.info(
                    "Creating FAISS index from chunks",
                    session_id=self.session_id,
                    chunk_count=len(chunks),
                    text_count=len(texts),
                )

                fm = FaissManager(self.faiss_dir, self.model_loader)
                vs = fm.load_or_create(texts=texts, metadatas=metas)

                #added = fm.add_documents(chunks)
                log.info(
                    "FAISS index updated",
                    chunk_count=len(chunks),        #-------------
                    #added=added,
                    index=str(self.faiss_dir),
                    session_id=self.session_id,
                )

                search_kwargs = {"k": k}
                if search_type == "mmr":
                    search_kwargs["fetch_k"] = fetch_k
                    search_kwargs["lambda_mult"] = lambda_mult
                    log.info(
                        "Using MMR search",
                        k=k,
                        fetch_k=fetch_k,
                        lambda_mult=lambda_mult,
                    )

                return vs.as_retriever(
                    search_type=search_type,
                    search_kwargs=search_kwargs,
                )

            if search_type == "pageindex":
                client = get_pageindex_client(self.cfg)

                doc_ids: List[str] = []
                for path in paths:
                    p = Path(path)
                    if p.suffix.lower() != ".pdf":
                        log.warning(
                            "Skipping non-PDF file for PageIndex",
                            path=str(path),
                        )
                        continue

                    try:
                        doc_id = submit_document(str(path), self.session_id, client)
                    except Exception as e:
                        log.error(
                            "PageIndex document upload failed",
                            session_id=self.session_id,
                            file_path=str(path),
                            error=str(e),
                        )
                        continue

                    doc_ids.append(doc_id)
                    log.info(
                        "PageIndex doc uploaded for session",
                        session_id=self.session_id,
                        file_path=str(path),
                        doc_id=doc_id,
                    )

                if not doc_ids:
                    raise DocumentPortalException(
                        "No valid PDFs uploaded for PageIndex",
                        "No PageIndex documents were uploaded successfully.",
                    )

                log.info(
                    "PageIndex documents submitted",
                    session_id=self.session_id,
                    doc_ids=doc_ids,
                )
                return doc_ids

            raise ValueError(f"Unsupported search_type: {search_type}")

        except DocumentPortalException as e:
            log.error(
                "Failed to build retriever",
                session_id=self.session_id,
                search_type=search_type,
                error=str(e),
                traceback=getattr(e, "traceback_str", ""),
            )
            raise
        except Exception as e:
            log.error(
                "Failed to build retriever",
                session_id=self.session_id,
                search_type=search_type,
                error=str(e),
            )
            raise DocumentPortalException(
                "Error building retriever",
                e,
            ) from e


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FaissManager:
    def __init__(self, faiss_dir: Path, model_loader: ModelLoader):
        self.faiss_dir = Path(faiss_dir)
        self.faiss_dir.mkdir(parents=True, exist_ok=True)
        self.model_loader = model_loader
        self.vs: Optional[FAISS] = None

    def _state_path(self) -> Path:
        return self.faiss_dir / "index_state.json"

    def _compute_fp(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> str:
        h = hashlib.sha256()
        for i, t in enumerate(texts):
            h.update(t.encode("utf-8", errors="ignore"))
            if metadatas and i < len(metadatas):
                h.update(json.dumps(metadatas[i], sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()

    def _load_state(self) -> Dict[str, Any]:
        p = self._state_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_state(self, state: Dict[str, Any]) -> None:
        self._state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")

    def load_or_create(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> FAISS:
        #embeddings = self.model_loader.get_embeddings_model()
        embeddings = self.model_loader.load_embeddings()
        index_name = (self.model_loader.config.get("vectorstore", {}) or {}).get("index_name", "index")
        #index_name = (self.model_loader.cfg.get("embeddings") or {}).get("faiss_index_name", "index")
        fp = self._compute_fp(texts, metadatas)
        state = self._load_state()
        same = state.get("fingerprint") == fp and state.get("index_name") == index_name

        if same:
            try:
                self.vs = FAISS.load_local(
                    str(self.faiss_dir),
                    embeddings,
                    index_name=index_name,
                    allow_dangerous_deserialization=True,
                )
                return self.vs
            except Exception as e:
                log.warning("Failed to load existing FAISS index; rebuilding", error=str(e))

        self.vs = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
        self.vs.save_local(str(self.faiss_dir), index_name=index_name)
        self._save_state({"fingerprint": fp, "index_name": index_name})
        return self.vs

    def add_documents(self, docs: List[Document]) -> int:
        if not docs:
            return 0
        if self.vs is None:
            raise ValueError("Vector store is not initialized. Call load_or_create() first.")

        index_name = "index"
        self.vs.add_documents(docs)
        self.vs.save_local(str(self.faiss_dir), index_name=index_name)
        return len(docs)
        # self.vs.add_documents(docs)
        # index_name = (self.model_loader.cfg.get("embeddings") or {}).get("faiss_index_name", "index")
        # self.vs.save_local(str(self.faiss_dir), index_name=index_name)
        # return len(docs)
