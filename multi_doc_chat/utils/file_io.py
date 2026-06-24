from __future__ import annotations
import uuid
from multi_doc_chat.logger.custom_logger import CustomLogger
from pathlib import Path
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable, List
from distro import name
from pkg_resources import safe_name
from multi_doc_chat.exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".pptx", ".docx", ".md", ".html", ".csv", ".json", ".xml", ".xlsx", ".xls", ".db", ".sqlite", ".sqlite3"}

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

      fname = f"{safe_name}_{uuid.uuid4().hex[:6]}{ext}"
      fname = f"{uuid.uuid4().hex[:8]}{ext}"

      out = target_dir / fname

      with open(out, "wb") as f:
        if hasattr(uf, "read"):
          f.write(uf.read())
        else:
          f.write(uf.getbuffer())   # fallback

      saved.append(out)

      log.info(
        "File saved for ingestion",
        uploaded=name,
        saved_as=str(out)
      )

    return saved

  except Exception as e:
    log.error(
        "Failed to save uploaded files",
        error=str(e),
        dir=str(target_dir)
      )

    raise DocumentPortalException("Failed to save uploaded files", e) from e