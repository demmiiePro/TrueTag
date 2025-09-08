# app_package/oauth2.py
"""
JWT utilities: token creation, verification, and current user dependencies.

This module handles:
- Access token creation (JWT).
- Token validation and decoding.
- Current user retrieval from DB with caching.
- Admin-only user retrieval for protected endpoints.

NOTE:
- Uses fastapi-cache with a temporary in-memory backend for the MVP.
- In production, use a shared cache (e.g., Redis) across workers.
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pydantic import ValidationError

from . import models, database
from .schemas.auth import TokenData
from .config import settings

# Initialize fastapi-cache with in-memory backend for MVP
# WARNING: Please note that this is not very safe for multi-worker deployments.
FastAPICache.init(InMemoryBackend())

# OAuth2 scheme: defines how users supply their token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.

    Args:
        data (dict): Payload to encode in the token (e.g., {"user_id": 1}).

    Returns:
        str: Encoded JWT token string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@cache(expire=settings.CACHE_EXPIRATION_SECONDS)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(database.get_db)
) -> models.User:
    """
    Validate JWT token and retrieve the authenticated user.

    This function is decorated with caching to reduce DB lookups during
    the lifetime of the token.

    Args:
        token (str): JWT token from the Authorization header.
        db (AsyncSession): SQLAlchemy async session.

    Returns:
        models.User: The authenticated user object.

    Raises:
        HTTPException: If the token is invalid or user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception

    result = await db.execute(
        select(models.User).where(models.User.id == token_data.id)
    )
    user = result.scalars().first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(database.get_db)
) -> models.User:
    """
    Ensure that the current authenticated user is an admin.

    This is used to secure admin-only endpoints (e.g., minting tags).

    Args:
        token (str): JWT token from Authorization header.
        db (AsyncSession): SQLAlchemy async session.

    Returns:
        models.User: The authenticated admin user object.

    Raises:
        HTTPException: If the user is not authenticated or not an admin.
    """
    user = await get_current_user(token=token, db=db)

    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only."
        )

    return user
