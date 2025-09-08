# app_package/schemas/scan.py
"""
Pydantic schemas for Scan model.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ScanBase(BaseModel):
    """
    Base schema for scans.
    """
    verification_result: str
    location: Optional[str] = None

class ScanResponse(ScanBase):
    """
    Schema for returning scan details.
    """
    id: int
    tag_id: int
    timestamp: datetime
    # Nested schemas for detailed data
    tag_code: str
    product_name: str
    product_description: Optional[str] = None
    product_category: str
    product_image_url: str

    class Config:
        from_attributes = True

class VerificationResponse(BaseModel):
    """
    Response schema for the public verify endpoint.
    """
    tag_id: int
    tag_code: str
    verification_result: str
    product_name: str
    product_description: Optional[str] = None
    product_category: str
    product_image_url: str
    timestamp: datetime