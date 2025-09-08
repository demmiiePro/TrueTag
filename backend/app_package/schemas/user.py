"""
Pydantic schemas for User model.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from ..schemas.tag import TagResponse



class UserBase(BaseModel):
    """
    Base schema for users.

    Attributes:
        email (EmailStr): User email.
        name (str): User's full name.
        role (str): Role (default 'manufacturer').
    """
    email: EmailStr
    name: Optional[str] = None
    role: str = "manufacturer"

class UserCreate(UserBase):
    """
    Schema for creating a new user.

    Attributes:
        password (str): Raw password before hashing.
    """
    password: str

class UserResponse(UserBase):
    """
    Schema for returning user details.

    Attributes:
        id (int): User ID.
        created_at (datetime): Account creation date.
        tags (List[TagResponse]): Tags owned by user.
    """
    id: int
    created_at: datetime
    # tags: List[TagResponse] = []

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    """
    Schema for requesting a password reset.

    Attributes:
        email (EmailStr): Email of the account to reset.
    """
    email: EmailStr

class PasswordReset(BaseModel):
    """
    Schema for performing a password reset.

    Attributes:
        token (str): Reset token.
        new_password (str): New password.
    """
    token: str
    new_password: str
