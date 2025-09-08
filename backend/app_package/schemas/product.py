"""
Pydantic schemas for Product model.
"""

from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, List
from .tag import TagResponse

class ProductMetadata(BaseModel):
    """
    Metadata for product details.

    Attributes:
        brand (str): Brand name.
        production_date (datetime): Manufacturing date.
        expiry_date (datetime): Expiration date.
    """
    brand: Optional[str] = None
    production_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

    @validator('production_date', 'expiry_date', pre=True)
    def parse_dates(cls, value):
        """Parses ISO strings into datetime objects."""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

class ProductBase(BaseModel):
    """
    Base schema for product.

    Attributes:
        name (str): Product name.
        description (str): Optional description.
        category (str): Product category.
        meta_data (ProductMetadata): Extra details about the product.
        status (str): Product status (default 'active').
    """
    name: str
    description: Optional[str] = None
    category: str
    meta_data: Optional[ProductMetadata] = None
    status: str = "active"

class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass

class ProductResponse(ProductBase):
    """
    Schema for returning product details.

    Attributes:
        id (int): Product ID.
        manufacturer_id (int): Owner ID.
        image_url (str): Image path or URL.
        created_at (datetime): Creation timestamp.
    """
    id: int
    manufacturer_id: int
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True
