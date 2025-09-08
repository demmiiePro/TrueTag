# app_package/models/scan.py
"""
Scan model for verification analytics.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Scan(Base):
    """
    Represents a verification attempt for a product tag.

    Attributes:
        id (int): Unique scan identifier.
        tag_id (int): Foreign key to the scanned tag.
        user_id (int): Foreign key to the user (optional for anonymous scans).
        location (str): Approximate location of scan (optional).
        verification_result (str): Verification outcome ('valid', 'invalid', 'duplicate').
        timestamp (datetime): Timestamp of scan.

    Relationships:
        tag (Tag): The tag that was scanned.
        user (User): The user who performed the scan.
    """

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location = Column(String, nullable=True)
    verification_result = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    tag = relationship("Tag", back_populates="scans")
    user = relationship("User", back_populates="scans")

    __table_args__ = (
        Index('ix_scans_tag_id', 'tag_id'),
        Index('ix_scans_timestamp', 'timestamp'),
    )
