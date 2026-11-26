"""CRUD Operations untuk Pengguna (User)."""

from typing import Optional
from sqlalchemy.orm import Session

from models.user import User
from crud.crud_gamification import get_or_create_profile


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_nim(db: Session, nim: str) -> Optional[User]:
    return db.query(User).filter(User.nim == nim.strip()).first()


def create_user(db: Session, nim: str, name: str, avatar: str = "👨‍💻") -> User:
    user = User(nim=nim.strip(), name=name.strip(), avatar=avatar)
    db.add(user)
    db.commit()
    db.refresh(user)
    # Otomatis buatkan profil gamifikasi MDA untuk user baru
    get_or_create_profile(db, user.id)
    return user


def get_or_create_default_user(db: Session) -> User:
    """Mengambil atau membuat user default untuk pengujian & demo skripsi."""
    default_nim = "2313020011"
    user = get_user_by_nim(db, default_nim)
    if not user:
        user = create_user(db, nim=default_nim, name="Bintang Maulana", avatar="👨‍💻")
    return user

