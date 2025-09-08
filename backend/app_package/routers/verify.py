# app_package/routers/verify.py
"""
Public API route for QR code verification.
Allows unauthenticated customers to scan tags and view product details.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Optional

from .. import models, database, schemas

router = APIRouter(
    prefix="/verify",
    tags=["Verification"]
)


@router.get("/{tag_code}", response_model=schemas.VerificationResponse)
async def verify_tag(
        tag_code: str,
        location: Optional[str] = None,
        db: AsyncSession = Depends(database.get_db)
) -> schemas.VerificationResponse:
    """
    Verify a QR code tag and return product details (public endpoint).

    Args:
        tag_code (str): Unique tag code from QR scan.
        location (str, optional): Scan location (e.g., GPS or region).
        db (AsyncSession): Database session for async operations.

    Returns:
        schemas.VerificationResponse: Product details and verification status.

    Raises:
        HTTPException: If tag is not found or invalid.
    """
    # CRITICAL: Removed @cache decorator. Each scan must be a new DB hit to check for duplicates.

    # 1. Fetch tag with product details
    tag_query = await db.execute(
        select(models.Tag)
        .where(models.Tag.tag_code == tag_code)
        .options(joinedload(models.Tag.product))
    )
    tag = tag_query.scalars().first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    # 2. Check for previous scans to determine if this is a duplicate
    existing_scan_query = await db.execute(
        select(models.Scan).where(models.Scan.tag_id == tag.id)
    )
    existing_scan = existing_scan_query.scalars().first()

    # 3. Determine verification status
    if not existing_scan and tag.status == "active":
        verification_result = "valid"
    elif existing_scan and tag.status == "active":
        verification_result = "duplicate"
    else:
        # This handles cases where status is "unused" or "flagged"
        verification_result = "invalid"

    # 4. Record the new scan
    scan = models.Scan(
        tag_id=tag.id,
        user_id=None,  # Public scan, no authenticated user
        location=location,
        verification_result=verification_result
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # 5. Prepare response
    product = tag.product
    if not product:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated product not found.")

    return schemas.VerificationResponse(
        tag_id=tag.id,
        tag_code=tag.tag_code,
        verification_result=verification_result,
        product_name=product.name,
        product_description=product.description,
        product_category=product.category,
        product_image_url=product.image_url,
        timestamp=scan.timestamp
    )