# app_package/models/tag.py
"""
Tag model representing blockchain-minted QR codes.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Tag(Base):
    """
    Represents a unique blockchain-minted QR tag.

    Attributes:
        id (int): Unique identifier for the tag.
        tag_code (str): Unique QR code string.
        token_id (str): Blockchain token ID.
        blockchain_tx_hash (str): Blockchain transaction hash for minting.
        status (str): Current tag status ('unused', 'active', 'flagged').
        product_id (int): Linked product ID.
        batch_id (int): Linked batch ID.
        created_at (datetime): Timestamp of tag creation.

    Relationships:
        product (Product): Linked product for this tag.
        batch (Batch): The batch this tag belongs to.
        scans (List[Scan]): Verification scans for this tag.
    """

    __tablename__ = "tags"


    id = Column(Integer, primary_key=True, index=True)
    tag_code = Column(String, unique=True, index=True, nullable=False)
    token_id = Column(String, unique=True, nullable=False)
    blockchain_tx_hash = Column(String, nullable=True)
    status = Column(String, default="unused", index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="tags")
    batch = relationship("Batch", back_populates="tags")
    scans = relationship("Scan", back_populates="tag")