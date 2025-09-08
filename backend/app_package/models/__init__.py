# app_package/models/__init__.py
from .user import User
from .product import Product
from .tag import Tag
from .scan import Scan
from .batch import Batch
from .password_reset_token import PasswordResetToken

# Explicitly register all models
__all__ = ["User", "Product", "Tag", "Scan", "Batch", "PasswordResetToken"]