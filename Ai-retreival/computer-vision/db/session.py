"""Konfigurasi Engine & Session Database SQLAlchemy 2.0."""

import os
import socket
from typing import Generator
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session

# Pastikan .env terbaca
load_dotenv(override=True)


def resolve_database_url() -> str:
    """Otomatis mendeteksi host database terbaik:
    - Jika host dari DATABASE_URL aktif: gunakan DATABASE_URL
    - Jika tidak, uji kandidat: host.containers.internal, 127.0.0.1, localhost, 10.89.0.1
    """
    env_url = os.getenv("DATABASE_URL")
    user = os.getenv("MYSQL_USER", "asisten")
    password = os.getenv("MYSQL_PASSWORD", "asisten123")
    database = os.getenv("MYSQL_DATABASE", "asisten_belajar_db")
    port = int(os.getenv("MYSQL_PORT", 3306))

    target_host = None
    if env_url:
        try:
            parsed = urlparse(env_url)
            if parsed.hostname:
                target_host = parsed.hostname
                port = parsed.port or port
        except Exception:
            pass

    candidates = []
    if target_host:
        candidates.append(target_host)
    for c in ["host.containers.internal", "127.0.0.1", "localhost", "10.89.0.1"]:
        if c not in candidates:
            candidates.append(c)

    for host in candidates:
        try:
            with socket.create_connection((host, port), timeout=0.6):
                print(f"✅ [Database] Berhasil terhubung ke host MySQL: {host}:{port}")
                if env_url and target_host == host:
                    return env_url
                return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        except Exception:
            continue

    print(
        f"⚠️ [Database] Server MySQL tidak merespons di kandidat: {candidates}.\n"
        f"👉 Harap aktifkan container database dengan perintah:\n"
        f"   podman start asisten_mysql  (atau docker compose up -d mysql)"
    )
    if env_url:
        return env_url
    return f"mysql+pymysql://{user}:{password}@127.0.0.1:{port}/{database}?charset=utf8mb4"


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
    """Dependency injection generator untuk FastAPI dengan penanganan error ramah."""
    db = SessionLocal()
    try:
        yield db
    except OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database MySQL tidak dapat dihubungi. "
                "Pastikan container MySQL aktif dengan perintah: podman start asisten_mysql "
                f"(Error: {exc.orig})"
            ),
        ) from exc
    finally:
        db.close()


