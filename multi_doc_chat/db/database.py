# multi_doc_chat/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from multi_doc_chat.utils.config_loader import load_config  # you already have this
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

config = load_config()

db_url = config.get("database", {}).get("url")

if db_url and db_url.startswith("env:"):
    env_name = db_url.split("env:", 1)[1].strip()
    db_url = os.getenv(env_name)

print("db_url =", repr(db_url))
if not db_url:
    # Fall back to env DATABASE_URL if not set in YAML
    db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise RuntimeError("DATABASE_URL not configured in config.yaml or .env")

engine = create_engine(db_url, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """
    Request-scoped DB session.
    Does NOT auto-commit. Callers (service layer) own transaction boundaries.
    Always closes the session at the end of the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()