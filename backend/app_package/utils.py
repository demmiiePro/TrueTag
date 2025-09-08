# app_package/utils.py
"""
Utility functions for password hashing and code generation.
"""

from passlib.context import CryptContext
import secrets
import string

# Use bcrypt for secure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The securely hashed password.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.

    Args:
        plain_password (str): The plain-text password provided by the user.
        hashed_password (str): The hashed password retrieved from the database.

    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def generate_unique_code(length: int = 16) -> str:
    """
    Generates a unique, URL-safe alphanumeric string.

    This function is suitable for generating short, unique identifiers like
    tag codes or API keys.

    Args:
        length (int): The desired length of the unique code.

    Returns:
        str: The generated unique code string.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))