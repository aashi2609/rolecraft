from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


ALLOWED_JWT_ALGORITHMS = ["HS256"]


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    token_version: int = 1,
    expires_minutes: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "token_version": token_version,
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate access token claims strictly against algorithm allowlist."""
    try:
        # Strictly reject 'none' or any algorithm not explicitly in allowlist
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
            },
        )
        return payload
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def create_refresh_token(
    *,
    user_id: UUID,
    token_version: int = 1,
    expires_days: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=expires_days or settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "token_version": token_version,
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate refresh token claims."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
            },
        )
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        return payload
    except JWTError as exc:
        raise ValueError("Invalid or expired refresh token") from exc


