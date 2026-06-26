from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Iterable, List

from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger.custom_logger import CustomLogger

log = CustomLogger().get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".pptx", ".docx", ".md", ".html", ".csv", ".json", ".xml", ".xlsx", ".xls", ".db", ".sqlite", ".sqlite3"}

def _read_uploaded_file_bytes(uploaded_file) -> bytes:
  """Return the full binary content for adapter and file-like upload objects."""
  if hasattr(uploaded_file, "getbuffer"):
    data = uploaded_file.getbuffer()
  elif hasattr(uploaded_file, "file"):
    uploaded_file.file.seek(0)
    data = uploaded_file.file.read()
  elif hasattr(uploaded_file, "read"):
    data = uploaded_file.read()
  else:
    raise TypeError(f"Unsupported uploaded file object: {type(uploaded_file)!r}")

  if isinstance(data, memoryview):
    data = data.tobytes()
  elif isinstance(data, bytearray):
    data = bytes(data)

  if not isinstance(data, bytes):
    raise TypeError(f"Uploaded file reader returned {type(data)!r}, expected bytes")

  return data

def save_uploaded_files(uploaded_files: Iterable, target_dir: Path) -> List[Path]:
  """Save uploaded files (Streamlit-like) and return their paths."""
  try:
    target_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for uf in uploaded_files:
      name = getattr(uf, "name", "file")
      ext = Path(name).suffix.lower()
      if ext not in SUPPORTED_EXTENSIONS:
        log.warning(f"Unsupported file skipped", filename = name)
        continue
      # Clean file name (only alphanum, dash, underscore)
      safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(name).stem).lower()

      fname = f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"

      out = target_dir / fname

      file_bytes = _read_uploaded_file_bytes(uf)

      with open(out, "wb") as f:
        f.write(file_bytes)

      saved.append(out)

      log.info(
        "File saved for ingestion",
        uploaded=name,
        saved_as=str(out),
        bytes_written=len(file_bytes),
      )

    return saved

  except Exception as e:
    log.error(
        "Failed to save uploaded files",
        error=str(e),
        dir=str(target_dir)
      )

    raise DocumentPortalException("Failed to save uploaded files", e) from e
