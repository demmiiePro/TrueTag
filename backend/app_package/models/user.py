# app_package/models/user.py
"""
User model for authentication and role-based access control.
"""

from sqlalchemy import Column, Integer, String, Index, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    """
    Represents a registered user in the system.

    Attributes:
        id (int): Unique identifier for the user.
        email (str): User's email address (must be unique).
        password (str): Hashed password for authentication.
        role (str): User role ('manufacturer', 'admin').
        name (str): Optional display name for the user.
        created_at (datetime): Timestamp of user creation.

    Relationships:
        products (List[Product]): Products owned by the user.
        scans (List[Scan]): Verification scans performed by the user.
        batches (List[Batch]): Batches of tags minted by the user.
        password_reset_tokens (List[PasswordResetToken]): Tokens issued to the user.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="manufacturer", index=True)  # manufacturer, admin
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    products = relationship("Product", back_populates="owner")
    scans = relationship("Scan", back_populates="user")
    batches = relationship("Batch", back_populates="manufacturer")  #
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")