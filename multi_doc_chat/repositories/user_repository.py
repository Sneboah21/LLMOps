from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from multi_doc_chat.db import models


def build_user(
    email: str,
    hashed_password: str,
) -> models.User:
    return models.User(
        email=email,
        hashed_password=hashed_password,
    )


def add_user(
    db: DBSession,
    user: models.User,
) -> models.User:
    db.add(user)
    return user


def get_user_by_email(
    db: DBSession,
    email: str,
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )


def get_user_by_id(
    db: DBSession,
    user_id: int,
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )