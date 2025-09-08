# app_package/models/product.py
"""
Product model representing manufacturer-owned goods.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Product(Base):
    """
    Represents a product registered by a manufacturer.

    Attributes:
        id (int): Unique identifier for the product.
        name (str): Product name.
        description (str): Optional product description.
        manufacturer_id (int): Foreign key to the `User` who owns the product.
        category (str): Category of the product (e.g., electronics, food).
        meta_data (dict): Additional structured details.
        image_url (str): Path or URL to product image.
        status (str): Product status ('active', 'inactive', 'draft').
        created_at (datetime): Timestamp of product creation.

    Relationships:
        owner (User): Manufacturer who owns the product.
        tags (List[Tag]): QR tags linked to this product.
        batches (List[Batch]): Batches of tags minted for this product.
    """

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    manufacturer_id = Column(Integer, ForeignKey("users.id"), index=True)
    category = Column(String, nullable=False, index=True)
    meta_data = Column(JSON, nullable=True)
    image_url = Column(String, nullable=False)
    status = Column(String, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="products")
    tags = relationship("Tag", back_populates="product")
    batches = relationship("Batch", back_populates="product")