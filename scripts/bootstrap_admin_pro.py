"""Bootstrap Admin Pro account: Clerk user, Pro tier in DB, ADMIN_API_KEY, .env patch."""

from __future__ import annotations

import os
import re
import secrets
import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.auth.clerk_jwt import update_clerk_plan_metadata
from backend.config import settings
from backend.models.user import User

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"

ENV_KEYS = (
    "ADMIN_PRO_USER_ID",
    "ADMIN_PRO_EMAIL",
    "ADMIN_PRO_PASSWORD",
    "ADMIN_API_KEY",
    "API_KEY_HASH_SALT",
)


def _generate_email() -> str:
    suffix = secrets.token_hex(4)
    return f"admin-pro-{suffix}@example.com"


def _generate_password() -> str:
    return secrets.token_urlsafe(24)


def _generate_admin_api_key() -> str:
    return secrets.token_hex(32)


def _generate_api_key_salt() -> str:
    return secrets.token_urlsafe(32)


def _read_env_file() -> str:
    if not ENV_PATH.exists():
        print(f"Error: {ENV_PATH} not found", file=sys.stderr)
        sys.exit(1)
    return ENV_PATH.read_text(encoding="utf-8")


def _get_env_value(content: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", content, re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def _patch_env_file(updates: dict[str, str]) -> None:
    content = _read_env_file()
    for key, value in updates.items():
        pattern = rf"^{re.escape(key)}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
        else:
            if "# Admin Pro account (bootstrap)" not in content:
                content = content.rstrip() + "\n\n# Admin Pro account (bootstrap)\n"
            content = content.rstrip() + f"\n{replacement}\n"
    ENV_PATH.write_text(content, encoding="utf-8")


def _verify_clerk_secret() -> None:
    if not settings.clerk_secret_key:
        print(
            "Error: CLERK_SECRET_KEY is not set in .env.\n"
            "Add Clerk keys from https://dashboard.clerk.com → API Keys.",
            file=sys.stderr,
        )
        sys.exit(1)


def _create_clerk_user(email: str, password: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.clerk.com/v1/users",
            headers={
                "Authorization": f"Bearer {settings.clerk_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email_address": [email],
                "password": password,
                "public_metadata": {"plan": "pro"},
            },
        )
    if response.status_code >= 400:
        print(f"Clerk API error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)
    data = response.json()
    user_id = data.get("id")
    if not user_id:
        print(f"Clerk API returned no user id: {data}", file=sys.stderr)
        sys.exit(1)
    return user_id


def _upsert_pro_user(session: Session, user_id: str, email: str) -> User:
    user = session.get(User, user_id)
    if user:
        user.email = email
        user.plan_tier = "pro"
    else:
        user = User(id=user_id, email=email, plan_tier="pro")
        session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _get_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def _print_summary(
    *,
    user_id: str,
    email: str,
    password: str | None,
    admin_api_key: str,
    reused: bool,
) -> None:
    print("\n=== Admin Pro Bootstrap Complete ===\n")
    print(f"  Clerk User ID:   {user_id}")
    print(f"  Email:           {email}")
    if password:
        print(f"  Password:        {password}")
    print(f"  Plan tier:       pro")
    print(f"  ADMIN_API_KEY:   {admin_api_key}")
    print(f"\n  Sign in at:      http://localhost:3000")
    print(f"  Admin dashboard: http://localhost:3000/admin")
    print(f"  (paste ADMIN_API_KEY on the admin page)")
    if reused:
        print("\n  (Reused existing ADMIN_PRO_USER_ID; no new password generated.)")
    print("\n  Credentials saved to .env\n")


def main() -> None:
    _verify_clerk_secret()
    env_content = _read_env_file()

    existing_user_id = _get_env_value(env_content, "ADMIN_PRO_USER_ID")
    existing_email = _get_env_value(env_content, "ADMIN_PRO_EMAIL")
    existing_admin_key = _get_env_value(env_content, "ADMIN_API_KEY")
    existing_salt = _get_env_value(env_content, "API_KEY_HASH_SALT")

    admin_api_key = existing_admin_key or _generate_admin_api_key()
    api_key_salt = existing_salt or _generate_api_key_salt()

    password: str | None = None
    if existing_user_id:
        user_id = existing_user_id
        email = existing_email or f"{user_id}@clerk.local"
        print(f"ADMIN_PRO_USER_ID already set ({user_id}); verifying Pro tier in DB...")
    else:
        email = os.environ.get("ADMIN_PRO_EMAIL") or _generate_email()
        password = os.environ.get("ADMIN_PRO_PASSWORD") or _generate_password()
        print(f"Creating Clerk user {email}...")
        user_id = _create_clerk_user(email, password)

    session = _get_session()
    try:
        user = _upsert_pro_user(session, user_id, email)
        update_clerk_plan_metadata(user.id, "pro")
    finally:
        session.close()

    env_updates: dict[str, str] = {
        "ADMIN_PRO_USER_ID": user_id,
        "ADMIN_PRO_EMAIL": email,
        "ADMIN_API_KEY": admin_api_key,
    }
    if password:
        env_updates["ADMIN_PRO_PASSWORD"] = password
    if not existing_salt:
        env_updates["API_KEY_HASH_SALT"] = api_key_salt

    _patch_env_file(env_updates)
    _print_summary(
        user_id=user_id,
        email=email,
        password=password,
        admin_api_key=admin_api_key,
        reused=bool(existing_user_id),
    )


if __name__ == "__main__":
    main()
