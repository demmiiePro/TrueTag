# app_package/models/batch.py
"""
Batch model for bulk tag minting.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Batch(Base):
    """
    Represents a batch of blockchain-minted tags.

    Attributes:
        id (int): Unique batch identifier.
        product_id (int): Foreign key to the product this batch is for.
        manufacturer_id (int): Foreign key to the `User` who minted the batch.
        count (int): Total number of tags in this batch.
        status (str): Status of the batch ('pending', 'minted', 'failed').
        blockchain_tx_hash (str): Blockchain transaction hash for the minting.
        created_at (datetime): Timestamp when the batch was created.

    Relationships:
        product (Product): The product this batch of tags is for.
        tags (List[Tag]): The individual tags within this batch.
    """

    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # optional
    manufacturer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    count = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, minted, assigned, failed
    mint_type = Column(String, default="warehouse")  # warehouse | direct
    blockchain_tx_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="batches")
    tags = relationship("Tag", back_populates="batch")
    manufacturer = relationship("User", back_populates="batches")  # ✅ FIX
