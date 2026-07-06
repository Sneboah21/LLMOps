from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.db import models
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.repositories import user_repository as user_repo

log = CustomLogger().get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(DocumentPortalException):
    pass


class AuthorizationError(DocumentPortalException):
    pass


class DuplicateUserError(DocumentPortalException):
    pass


class InvalidTokenError(DocumentPortalException):
    pass


class AuthService:
    def __init__(self, db: DBSession, cfg: dict):
        self.db = db
        self.cfg = cfg

    def _auth_cfg(self) -> dict:
        auth_cfg = self.cfg.get("auth", {})
        if not auth_cfg:
            raise DocumentPortalException("Missing auth configuration.")
        return auth_cfg

    def _resolve_secret(self) -> str:
        raw = self._auth_cfg().get("jwt_secret_key")
        if not raw:
            raise DocumentPortalException("Missing JWT secret configuration.")

        if isinstance(raw, str) and raw.startswith("env:"):
            env_name = raw.split("env:", 1)[1].strip()
            value = os.getenv(env_name)
            if not value:
                raise DocumentPortalException(
                    f"Environment variable '{env_name}' is not set."
                )
            return value

        return str(raw)

    def get_algorithm(self) -> str:
        return str(self._auth_cfg().get("jwt_algorithm", "HS256"))

    def get_expire_minutes(self) -> int:
        return int(self._auth_cfg().get("access_token_expire_minutes", 60))

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def validate_password_strength(self, password: str) -> None:
        if len(password) < 8:
            raise DocumentPortalException("Password must be at least 8 characters long.")
        if password.lower() == password:
            raise DocumentPortalException("Password must contain at least one uppercase letter.")
        if password.upper() == password:
            raise DocumentPortalException("Password must contain at least one lowercase letter.")
        if not any(ch.isdigit() for ch in password):
            raise DocumentPortalException("Password must contain at least one digit.")
        if password.isalnum():
            raise DocumentPortalException("Password must contain at least one special character.")

    def register_user(
        self,
        email: EmailStr,
        password: str,
        confirm_password: str,
    ) -> models.User:
        if password != confirm_password:
            raise DocumentPortalException("Passwords do not match.")

        self.validate_password_strength(password)

        existing = user_repo.get_user_by_email(self.db, str(email))
        if existing is not None:
            raise DuplicateUserError("A user with this email already exists.")

        user = user_repo.build_user(
            email=str(email),
            hashed_password=self.hash_password(password),
        )
        user_repo.add_user(self.db, user)
        self.db.flush()
        self.db.refresh(user)

        log.info(
            "User registered",
            user_id=user.id,
            email=user.email,
        )
        return user

    def authenticate_user(
        self,
        email: EmailStr,
        password: str,
    ) -> models.User:
        user = user_repo.get_user_by_email(self.db, str(email))
        if user is None or not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        return user

    def create_access_token(
        self,
        user: models.User,
    ) -> tuple[str, int]:
        expire_minutes = self.get_expire_minutes()
        expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": expire_at,
        }

        token = jwt.encode(
            payload,
            self._resolve_secret(),
            algorithm=self.get_algorithm(),
        )
        return token, expire_minutes * 60

    def verify_token(
        self,
        token: str,
    ) -> models.User:
        try:
            payload = jwt.decode(
                token,
                self._resolve_secret(),
                algorithms=[self.get_algorithm()],
            )
            sub = payload.get("sub")
            if sub is None:
                raise InvalidTokenError("Token payload is missing subject.")

            user = user_repo.get_user_by_id(self.db, int(sub))
            if user is None:
                raise InvalidTokenError("Token user does not exist.")

            return user

        except JWTError as e:
            raise InvalidTokenError("Invalid or expired token.", e) from e