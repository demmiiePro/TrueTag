# app_package/routers/auth.py
"""
Authentication endpoints: register, login (OAuth2), password-reset request and reset.

Google-style docstrings are used to help frontend and other devs consume these routes.
"""

from datetime import datetime, timedelta, timezone
import secrets
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .. import models, oauth2, utils, schemas
from ..database import get_db
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new manufacturer user.

    Args:
        user_in (schemas.UserCreate): Email, password, optional name.
        db (AsyncSession): Database session.

    Returns:
        schemas.UserResponse: Created user data (without password).

    Raises:
        HTTPException: 400 if email already exists.
    """
    # Prevent duplicate accounts
    q = await db.execute(select(models.User).where(models.User.email == user_in.email))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Hash password and create user
    hashed = utils.hash_password(user_in.password)
    # CRITICAL SECURITY FIX: Do not allow users to specify their own role on registration.
    # New users should always be a default role, like 'manufacturer'.
    user = models.User(email=user_in.email, password=hashed, name=user_in.name, role="manufacturer")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return schemas.UserResponse.from_orm(user)


@router.post("/login", response_model=schemas.Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user and return a JWT token (OAuth2 password flow).

    Args:
        form_data (OAuth2PasswordRequestForm): username=email, password.
        db (AsyncSession): Database session.

    Returns:
        schemas.Token: access_token and token_type.

    Raises:
        HTTPException: 401 if credentials invalid.
    """
    q = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = q.scalars().first()
    if not user or not utils.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = oauth2.create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/password-reset-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(payload: schemas.PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """
    Request a password reset link/token. Token is logged for now (replace with email).

    Args:
        payload (PasswordResetRequest): { email: str }
        db (AsyncSession): Database session.

    Returns:
        dict: Generic response to avoid account enumeration.
    """
    q = await db.execute(select(models.User).where(models.User.email == payload.email))
    user = q.scalars().first()
    if not user:
        # Return generic response to avoid account enumeration
        return {"detail": "If an account exists, a reset link will be sent"}

    # Use a secure token generation and expiration
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    reset_record = models.PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset_record)
    await db.commit()

    # TODO: Replace logger.info with a secure email sending integration.
    logger.info("Password reset token for %s: %s", payload.email, token)
    return {"detail": "If an account exists, a reset link will be sent"}

@router.post("/password-reset", status_code=status.HTTP_200_OK)
async def reset_password(payload: schemas.PasswordReset, db: AsyncSession = Depends(get_db)):
    """
    Reset a password using the reset token.

    Args:
        payload (PasswordReset): { token: str, new_password: str }
        db (AsyncSession): Database session.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: 400 if token invalid or expired.
    """
    q = await db.execute(select(models.PasswordResetToken).where(models.PasswordResetToken.token == payload.token))
    token_rec = q.scalars().first()
    now = datetime.now(timezone.utc)

    if not token_rec or token_rec.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    # Update the user's password
    user_q = await db.execute(select(models.User).where(models.User.id == token_rec.user_id))
    user = user_q.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Associated user not found")

    user.password = utils.hash_password(payload.new_password)

    # Clean up token (delete)
    await db.delete(token_rec)
    await db.commit()
    return {"detail": "Password reset successfully"}


