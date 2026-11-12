"""Commandes d'administration : python -m app.cli create-admin --email ... [--name ...]

Le mot de passe est lu dans ADMIN_PASSWORD ou demandé en interactif (jamais en argument,
pour ne pas finir dans l'historique du shell ni dans `ps`).
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, UserRole
from app.security import hash_password


def create_admin(db: Session, email: str, password: str, name: str = "Administrateur") -> User:
    if len(password) < 10:
        raise ValueError("Mot de passe : 10 caractères minimum")
    email = email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ValueError("Un compte existe déjà avec cet email")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=name,
        role=UserRole.ADMIN,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Administrateur")
    args = parser.parse_args(argv)

    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Mot de passe admin : ")
    with SessionLocal() as db:
        try:
            user = create_admin(db, args.email, password, args.name)
        except ValueError as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 1
    print(f"Admin créé : {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
