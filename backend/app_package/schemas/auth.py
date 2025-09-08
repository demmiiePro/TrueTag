"""
Schemas for authentication and JWT token handling.
"""

from pydantic import BaseModel

class Token(BaseModel):
    """
    Represents an authentication token.

    Attributes:
        access_token (str): JWT access token string.
        token_type (str): Type of the token (e.g., 'bearer').
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Represents decoded JWT payload.

    Attributes:
        id (int): User ID extracted from token.
    """
    id: int
