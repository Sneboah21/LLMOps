from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from multi_doc_chat.db import models
from multi_doc_chat.db.database import get_db
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.services.auth_service import AuthService
from multi_doc_chat.utils.config_loader import load_config

bearer_scheme = HTTPBearer(auto_error=True)
CONFIG = load_config()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        token = credentials.credentials
        service = AuthService(db=db, cfg=CONFIG)
        return service.verify_token(token)

    except DocumentPortalException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )