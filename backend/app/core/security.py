from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# Argon2id password hasher with production-grade parameters
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def hash_token(token: str) -> str:
    """SHA-256 hash for secure storage of refresh tokens in database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically strong random token."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    tenant_id: Optional[uuid.UUID] = None,
    role: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    is_superadmin: bool = False,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token containing subject, tenant, and RBAC claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "is_superadmin": is_superadmin,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if tenant_id:
        claims["tenant_id"] = str(tenant_id)
    if role:
        claims["role"] = role
    if permissions:
        claims["permissions"] = permissions

    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token, returning the payload claims."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise
