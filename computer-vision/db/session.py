"""Konfigurasi Engine & Session Database SQLAlchemy 2.0."""

import os
import socket
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

def resolve_database_url() -> str:
    """Otomatis mendeteksi host database terbaik:
    - Jika dijalankan di host lokal: 127.0.0.1
    - Jika dijalankan di dalam container devcontainer: host.containers.internal / 10.89.0.1
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    candidates = ["127.0.0.1", "host.containers.internal", "10.89.0.1"]
    for host in candidates:
        try:
            with socket.create_connection((host, 3306), timeout=0.5):
                return f"mysql+pymysql://asisten:asisten123@{host}:3306/asisten_belajar_db?charset=utf8mb4"
        except Exception:
            continue
    return "mysql+pymysql://asisten:asisten123@127.0.0.1:3306/asisten_belajar_db?charset=utf8mb4"

DATABASE_URL = resolve_database_url()

# Engine dengan connection pool pre-ping (mencegah broken pipe / connection drop)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Factory session lokal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection generator untuk FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

