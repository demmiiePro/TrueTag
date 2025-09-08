# app_package/routers/users.py
"""
API routes for user profile and role management.
Handles profile retrieval/updates and admin role changes.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from .. import models, oauth2, database, schemas

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None

class RoleUpdate(BaseModel):
    role: str # manufacturer, admin

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_profile(
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.UserResponse:
    """
    Retrieve the current user's profile.

    Args:
        current_user (models.User): Authenticated user object (already fetched by dependency).

    Returns:
        schemas.UserResponse: User profile details.
    """
    # The `current_user` object is already loaded, so no need for a redundant DB query.
    return schemas.UserResponse.from_orm(current_user)

@router.put("/me", response_model=schemas.UserResponse)
async def update_current_user_profile(
    update: UserUpdate,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.UserResponse:
    """
    Update the current user's profile (email, name).

    Args:
        update (UserUpdate): Updated profile data.
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user.

    Returns:
        schemas.UserResponse: Updated user profile.

    Raises:
        HTTPException: If email is already taken or user not found.
    """
    if update.email and update.email != current_user.email:
        # Check for email uniqueness
        email_query = await db.execute(
            select(models.User).where(models.User.email == update.email)
        )
        if email_query.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
        current_user.email = update.email

    if update.name is not None:
        current_user.name = update.name

    await db.commit()
    await db.refresh(current_user)

    return schemas.UserResponse.from_orm(current_user)

@router.put("/{id}/role", response_model=schemas.UserResponse)
async def update_user_role(
    id: int,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.UserResponse:
    """
    Update a user's role (admin-only).

    Args:
        id (int): User ID to update.
        role_update (RoleUpdate): New role (manufacturer, admin).
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be admin).

    Returns:
        schemas.UserResponse: Updated user profile.

    Raises:
        HTTPException: If user not found, invalid role, or not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update roles")

    # This check is crucial to prevent the function from attempting to update
    # to an invalid role. Consider using an Enum for roles in a larger project.
    if role_update.role not in ["manufacturer", "admin"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user_query = await db.execute(
        select(models.User).where(models.User.id == id)
    )
    user = user_query.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = role_update.role
    await db.commit()
    await db.refresh(user)

    return schemas.UserResponse.from_orm(user)