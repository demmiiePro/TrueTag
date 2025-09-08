# app_package/models/password_reset_token.py
"""
Password reset token model for account recovery.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class PasswordResetToken(Base):
    """
    Represents a token for password reset.

    Attributes:
        id (int): Unique token record ID.
        user_id (int): Foreign key to the `User` requesting reset.
        token (str): Unique reset token string.
        expires_at (datetime): Expiration date/time of the token.

    Relationships:
        user (User): User associated with the token.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")