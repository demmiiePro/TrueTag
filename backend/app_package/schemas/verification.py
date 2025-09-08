"""
Schema for public tag verification response.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VerificationResponse(BaseModel):
    """
    Represents the result of a public tag verification.

    Attributes:
        tag_id (int): Verified tag ID.
        tag_code (str): The QR code string.
        verification_result (str): 'valid', 'invalid', or 'duplicate'.
        product_name (str): Linked product name.
        product_category (str): Linked product category.
        product_brand (str): Optional brand name.
        scan_id (int): ID of recorded scan.
        scan_timestamp (datetime): When the scan was recorded.
        scan_location (str): Optional scan location.
    """
    tag_id: int
    tag_code: str
    verification_result: str
    product_name: str
    product_category: str
    product_brand: Optional[str]
    scan_id: int
    scan_timestamp: datetime
    scan_location: Optional[str]

    class Config:
        from_attributes = True
