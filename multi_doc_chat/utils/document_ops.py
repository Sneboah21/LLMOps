from __future__ import annotations

import base64
import re
import zlib
from pathlib import Path
from typing import Iterable, List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from fastapi import UploadFile

log = CustomLogger().get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

_PDF_OBJECT_RE = re.compile(
    rb"(\d+)\s+(\d+)\s+obj(.*?)endobj",
    re.S,
)
_PDF_PAGE_CONTENT_RE = re.compile(rb"/Contents\s+(\[.*?\]|\d+\s+\d+\s+R)", re.S)
_PDF_REF_RE = re.compile(rb"(\d+)\s+(\d+)\s+R")
_PDF_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\s*endstream", re.S)
_PDF_FILTER_ARRAY_RE = re.compile(rb"/Filter\s*\[(.*?)\]", re.S)
_PDF_FILTER_NAME_RE = re.compile(rb"/Filter\s*/([A-Za-z0-9]+)")
_PDF_TJ_RE = re.compile(r"\[(.*?)\]\s*TJ", re.S)
_PDF_TJ_ARRAY_STRING_RE = re.compile(r"\((?:\\.|[^\\)])*\)")
_PDF_TJ_SINGLE_RE = re.compile(r"\((?:\\.|[^\\)])*\)\s*Tj", re.S)


def _decode_pdf_literal(text: str) -> str:
    """Decode a PDF literal string, handling basic escape sequences."""
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]

    result: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch != "\\":
            result.append(ch)
            i += 1
            continue

        i += 1
        if i >= len(text):
            result.append("\\")
            break

        esc = text[i]
        mapping = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "b": "\b",
            "f": "\f",
            "\\": "\\",
            "(": "(",
            ")": ")",
        }
        if esc in mapping:
            result.append(mapping[esc])
            i += 1
            continue

        if esc in "\n\r":
            if esc == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            continue

        if esc in "01234567":
            octal = esc
            i += 1
            for _ in range(2):
                if i < len(text) and text[i] in "01234567":
                    octal += text[i]
                    i += 1
                else:
                    break
            result.append(chr(int(octal, 8)))
            continue

        result.append(esc)
        i += 1

    return "".join(result)


def _apply_pdf_filters(stream_data: bytes, filters: List[str]) -> bytes:
    """Apply a PDF stream's filters in declaration order."""
    data = stream_data
    for filter_name in filters:
        if filter_name == "ASCII85Decode":
            cleaned = data.strip()
            if not cleaned.endswith(b"~>"):
                cleaned += b"~>"
            data = base64.a85decode(cleaned, adobe=True)
        elif filter_name == "FlateDecode":
            data = zlib.decompress(data)
        else:
            raise ValueError(f"Unsupported PDF filter: {filter_name}")
    return data


def _extract_text_from_pdf_stream(decoded_stream: bytes) -> str:
    stream_text = decoded_stream.decode("latin1", errors="ignore")
    pieces: List[str] = []

    for match in _PDF_TJ_SINGLE_RE.finditer(stream_text):
        literal = match.group(0).rsplit(")", 1)[0] + ")"
        pieces.append(_decode_pdf_literal(literal))

    for match in _PDF_TJ_RE.finditer(stream_text):
        array_body = match.group(1)
        fragments = [
            _decode_pdf_literal(item)
            for item in _PDF_TJ_ARRAY_STRING_RE.findall(array_body)
        ]
        if fragments:
            pieces.append("".join(fragments))

    cleaned = "\n".join(part.strip() for part in pieces if part.strip())
    return cleaned


def _load_pdf_with_fallback(path: Path) -> List[Document]:
    """Load text from simple text-based PDFs without external PDF dependencies."""
    raw = path.read_bytes()
    objects = {
        int(match.group(1)): match.group(3)
        for match in _PDF_OBJECT_RE.finditer(raw)
    }
    page_docs: List[Document] = []

    for obj_num, body in objects.items():
        if b"/Type /Page" not in body or b"/Type /Pages" in body:
            continue

        contents_match = _PDF_PAGE_CONTENT_RE.search(body)
        if not contents_match:
            continue

        content_refs = [
            int(ref_match.group(1))
            for ref_match in _PDF_REF_RE.finditer(contents_match.group(1))
        ]

        page_text_parts: List[str] = []
        for ref in content_refs:
            stream_obj = objects.get(ref)
            if not stream_obj:
                continue

            stream_match = _PDF_STREAM_RE.search(stream_obj)
            if not stream_match:
                continue

            filters: List[str] = []
            filter_array_match = _PDF_FILTER_ARRAY_RE.search(stream_obj)
            if filter_array_match:
                filters = [
                    name.decode("latin1")
                    for name in re.findall(rb"/([A-Za-z0-9]+)", filter_array_match.group(1))
                ]
            else:
                filter_name_match = _PDF_FILTER_NAME_RE.search(stream_obj)
                if filter_name_match:
                    filters = [filter_name_match.group(1).decode("latin1")]

            stream_data = stream_match.group(1).strip()
            decoded_stream = _apply_pdf_filters(stream_data, filters)
            extracted = _extract_text_from_pdf_stream(decoded_stream)
            if extracted:
                page_text_parts.append(extracted)

        page_text = "\n".join(part for part in page_text_parts if part).strip()
        if not page_text:
            continue

        page_docs.append(
            Document(
                page_content=page_text,
                metadata={"source": str(path), "page_object": obj_num},
            )
        )

    if not page_docs:
        raise ValueError("Fallback PDF parser could not extract any text.")

    return page_docs


def load_documents(paths: Iterable[Path]) -> List[Document]:
    """Load docs using appropriate loader based on extension."""

    docs: List[Document] = []
    path_list = [Path(p) for p in paths]

    try:
        log.info(
            "Starting document load",
            path_count=len(path_list),
            paths=[str(p) for p in path_list],
        )

        for p in path_list:
            ext = p.suffix.lower()
            exists = p.exists()
            size = p.stat().st_size if exists else None

            log.info(
                "Loading document path",
                path=str(p),
                extension=ext,
                exists=exists,
                size_bytes=size,
            )

            if ext == ".pdf":
                try:
                    loader = PyPDFLoader(str(p))
                    loaded_docs = loader.load()
                except Exception as pdf_error:
                    log.warning(
                        "PyPDFLoader failed, using PDF fallback",
                        path=str(p),
                        error=str(pdf_error),
                    )
                    loaded_docs = _load_pdf_with_fallback(p)

            elif ext == ".docx":
                loader = Docx2txtLoader(str(p))
                loaded_docs = loader.load()

            elif ext == ".txt":
                loader = TextLoader(str(p), encoding="utf-8")
                loaded_docs = loader.load()

            else:
                log.warning(
                    "Unsupported extension skipped",
                    path=str(p)
                )
                continue

            docs.extend(loaded_docs)

            log.info(
                "Document path loaded",
                path=str(p),
                loaded_count=len(loaded_docs),
            )

        log.info(
            "Documents loaded",
            count=len(docs),
            paths=[str(p) for p in path_list],
        )

        return docs

    except Exception as e:
        log.exception(
            "Failed loading documents",
            error=str(e),
            attempted_paths=[str(p) for p in path_list],
        )

        raise DocumentPortalException(
            "Error loading documents",
            e
        ) from e

class FastAPIFileAdapter:
    """
    Adapt FastAPI UploadFile to a simple object with .name and .getbuffer()
    """
    def __init__(self, uf: UploadFile, prefetched: bytes = b""):
        self._uf = uf
        self._data = prefetched if prefetched else None
        self.name = uf.filename or "file"
    
    def getbuffer(self) -> bytes:
        # Prefer the eagerly prefetched UploadFile bytes when available.
        if self._data is not None:
            return self._data
        self._uf.file.seek(0)  # Ensure we're at the start of the file
        data = self._uf.file.read()
        if isinstance(data, memoryview):
            return data.tobytes()
        if isinstance(data, bytearray):
            return bytes(data)
        return data

    def read(self) -> bytes:
        return self.getbuffer()
