from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable, List

from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader

from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger.custom_logger import CustomLogger

log = CustomLogger().get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FastAPIFileAdapter:
    def __init__(self, upload_file: UploadFile, prefetched: bytes | None = None):
        self.upload_file = upload_file
        self.name = upload_file.filename or "file"
        self.content_type = getattr(upload_file, "content_type", None)
        self._prefetched = prefetched
        self.file = BytesIO(prefetched) if prefetched is not None else upload_file.file

    def read(self, *args, **kwargs):
        if self._prefetched is not None:
            return self.file.read(*args, **kwargs)
        return self.upload_file.file.read(*args, **kwargs)

    def seek(self, offset: int, whence: int = 0):
        if self._prefetched is not None:
            return self.file.seek(offset, whence)
        return self.upload_file.file.seek(offset, whence)

    def getbuffer(self):
        if self._prefetched is not None:
            return memoryview(self._prefetched)

        current_pos = self.upload_file.file.tell()
        try:
            self.upload_file.file.seek(0)
            data = self.upload_file.file.read()
        finally:
            self.upload_file.file.seek(current_pos)
        return memoryview(data)


class MissingPdfDependencyError(DocumentPortalException):
    pass


class CorruptedPdfError(DocumentPortalException):
    pass


class EncryptedPdfError(DocumentPortalException):
    pass


class UnsupportedDocumentFormatError(DocumentPortalException):
    pass


class DocumentIOError(DocumentPortalException):
    pass


class DocumentLoadError(DocumentPortalException):
    pass


class AllDocumentsFailedError(DocumentPortalException):
    pass


try:
    import pypdf.errors as pypdf_errors
except Exception:
    pypdf_errors = None


try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


class _DocumentLoadFailure(Exception):
    def __init__(self, message: str, *, filename: str, cause: Exception):
        super().__init__(message)
        self.filename = filename
        self.cause = cause



def normalize_uploaded_files(files: list[UploadFile]) -> list[UploadFile]:
    if not files:
        raise ValueError("No files uploaded.")
    return files



def _classify_pdf_exception(path: Path, error: Exception) -> DocumentPortalException:
    message = str(error)
    lower_message = message.lower()

    if isinstance(error, ImportError) or "pypdf package not found" in lower_message:
        return MissingPdfDependencyError(
            f"Missing PDF dependency for '{path.name}': install 'pypdf' to enable PDF ingestion.",
            error,
        )

    if pypdf_errors is not None:
        file_not_decrypted = getattr(pypdf_errors, "FileNotDecryptedError", None)
        pdf_read_error = getattr(pypdf_errors, "PdfReadError", None)

        if file_not_decrypted is not None and isinstance(error, file_not_decrypted):
            return EncryptedPdfError(
                f"Encrypted PDF '{path.name}' cannot be processed without a password.",
                error,
            )

        if pdf_read_error is not None and isinstance(error, pdf_read_error):
            if "encrypted" in lower_message or "decrypt" in lower_message:
                return EncryptedPdfError(
                    f"Encrypted PDF '{path.name}' cannot be processed without a password.",
                    error,
                )
            return CorruptedPdfError(
                f"Corrupted or unreadable PDF '{path.name}' could not be parsed.",
                error,
            )

    if "encrypted" in lower_message or "decrypt" in lower_message:
        return EncryptedPdfError(
            f"Encrypted PDF '{path.name}' cannot be processed without a password.",
            error,
        )

    if any(token in lower_message for token in ["truncated", "incomplete", "malformed", "corrupt", "xref", "eof"]):
        return CorruptedPdfError(
            f"Corrupted or unreadable PDF '{path.name}' could not be parsed.",
            error,
        )

    if isinstance(error, OSError):
        return DocumentIOError(
            f"I/O error while reading PDF '{path.name}'.",
            error,
        )

    return DocumentLoadError(
        f"Failed to load PDF '{path.name}'.",
        error,
    )



def _classify_generic_exception(path: Path, error: Exception) -> DocumentPortalException:
    if isinstance(error, OSError):
        return DocumentIOError(f"I/O error while reading '{path.name}'.", error)
    return DocumentLoadError(f"Failed to load document '{path.name}'.", error)



def _count_pdf_pages(path: Path) -> int | None:
    if PdfReader is None:
        return None
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            return None
        return len(reader.pages)
    except Exception:
        return None



def _load_pdf_with_pypdf(path: Path) -> List[Document]:
    try:
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
    except Exception as error:
        raise _DocumentLoadFailure(
            f"Failed to load PDF '{path.name}' with PyPDFLoader.",
            filename=path.name,
            cause=_classify_pdf_exception(path, error),
        ) from error

    page_count = _count_pdf_pages(path)
    log.info(
        "Document loaded",
        filename=path.name,
        loader="PyPDFLoader",
        pages_extracted=page_count if page_count is not None else len(loaded_docs),
        documents_produced=len(loaded_docs),
    )
    return loaded_docs



def _load_non_pdf_document(path: Path) -> List[Document]:
    ext = path.suffix.lower()
    if ext == ".docx":
        loader_name = "Docx2txtLoader"
        loader = Docx2txtLoader(str(path))
    elif ext == ".txt":
        loader_name = "TextLoader"
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        raise _DocumentLoadFailure(
            f"Unsupported document format: {path.name}",
            filename=path.name,
            cause=UnsupportedDocumentFormatError(
                f"Unsupported document format '{ext or '<none>'}' for file '{path.name}'."
            ),
        )

    try:
        loaded_docs = loader.load()
    except Exception as error:
        raise _DocumentLoadFailure(
            f"Failed to load document '{path.name}'.",
            filename=path.name,
            cause=_classify_generic_exception(path, error),
        ) from error

    log.info(
        "Document loaded",
        filename=path.name,
        loader=loader_name,
        pages_extracted=1,
        documents_produced=len(loaded_docs),
    )
    return loaded_docs



def load_documents(paths: Iterable[Path]) -> List[Document]:
    path_list = [Path(raw_path) for raw_path in paths]
    successful_docs: List[Document] = []
    failures: List[DocumentPortalException] = []

    try:
        for path in path_list:
            ext = path.suffix.lower()

            if ext not in SUPPORTED_EXTENSIONS:
                error = UnsupportedDocumentFormatError(
                    f"Unsupported document format '{ext or '<none>'}' for file '{path.name}'."
                )
                failures.append(error)
                log.error(
                    "Document load failed",
                    filename=path.name,
                    loader="unsupported",
                    error=str(error),
                    exception_type=type(error).__name__,
                )
                continue

            try:
                loaded_docs = _load_pdf_with_pypdf(path) if ext == ".pdf" else _load_non_pdf_document(path)
            except _DocumentLoadFailure as failure:
                classified = (
                    failure.cause
                    if isinstance(failure.cause, DocumentPortalException)
                    else DocumentLoadError(str(failure.cause), failure.cause)
                )
                failures.append(classified)
                log.error(
                    "Document load failed",
                    filename=path.name,
                    loader="PyPDFLoader" if ext == ".pdf" else {".docx": "Docx2txtLoader", ".txt": "TextLoader"}.get(ext, ext),
                    error=str(classified),
                    exception_type=type(classified).__name__,
                    traceback=getattr(classified, "traceback_str", ""),
                )
                continue

            successful_docs.extend(loaded_docs)

        if successful_docs:
            log.info(
                "Document loading complete",
                files_processed=len(path_list),
                documents_loaded=len(successful_docs),
                failed_files=len(failures),
            )
            return successful_docs

        if failures:
            summary = "; ".join(str(failure) for failure in failures)
            raise AllDocumentsFailedError(
                f"Failed to load all uploaded documents. {summary}",
                failures[0],
            )

        raise AllDocumentsFailedError("No documents were provided for loading.")

    except DocumentPortalException:
        raise
    except Exception as e:
        raise DocumentPortalException("Unexpected error in load_documents", e) from e
