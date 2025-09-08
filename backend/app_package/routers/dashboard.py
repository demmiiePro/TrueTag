# app_package/routers/dashboard.py
"""
API routes for manufacturer analytics.
Provides scan statistics and detailed scan records for dashboard visualization.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer
from sqlalchemy.orm import joinedload
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, validator
from fastapi_cache.decorator import cache

from .. import models, oauth2, database, schemas

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


class DateFilter(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None

    @validator('end_date')
    def end_date_after_start(cls, end_date, values):
        if end_date and 'start_date' in values and values['start_date'] and end_date < values['start_date']:
            raise ValueError("end_date must be after start_date")
        return end_date


@router.get("/stats", response_model=Dict[str, Any])
@cache(expire=300)  # Cache for 5 minutes
async def get_dashboard_stats(
        date_filter: DateFilter = Depends(),
        product_id: int | None = None,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
) -> Dict[str, Any]:
    """
    Retrieve dashboard statistics for a manufacturer.

    Args:
        date_filter (DateFilter): Optional date range for filtering.
        product_id (int, optional): Filter by a specific product.
        db (AsyncSession): Database session.
        current_user (models.User): Authenticated user.

    Returns:
        dict: A dictionary of key metrics (total scans, scans by month).

    Raises:
        HTTPException: If user is not a manufacturer or product not owned.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can access dashboard")

    # Fetch total scans for the manufacturer
    total_scans_query = select(func.count(models.Scan.id)).where(models.Scan.user_id == current_user.id)
    total_scans_result = await db.execute(total_scans_query)
    total_scans = total_scans_result.scalar_one()

    # Fetch scan counts by month
    scans_by_month_query = select(
        func.strftime('%Y-%m', models.Scan.timestamp).label('month'),
        func.count(models.Scan.id).label('scan_count')
    ).where(models.Scan.user_id == current_user.id).group_by('month').order_by('month')
    scans_by_month_result = await db.execute(scans_by_month_query)
    scans_by_month = [
        {"month": r.month, "scan_count": r.scan_count} for r in scans_by_month_result.all()
    ]

    # This is the correct way to load the data for the scans endpoint
    scans_query = select(models.Scan).join(models.Tag, models.Scan.tag_id == models.Tag.id).join(models.Product,
                                                                                                 models.Tag.product_id == models.Product.id).where(
        models.Product.manufacturer_id == current_user.id)
    # The rest of the logic remains the same

    return {
        "total_scans": total_scans,
        "scans_by_month": scans_by_month
    }


# This is the corrected version of the `get_dashboard_scans` function
@router.get("/scans", response_model=List[schemas.ScanResponse])
async def get_dashboard_scans(
        date_filter: DateFilter = Depends(),
        product_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
) -> List[schemas.ScanResponse]:
    """
    Retrieve detailed scan records for a manufacturer's products.
    ...
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can access dashboard")

    # The corrected query with explicit join conditions
    query = select(models.Scan).join(models.Tag, models.Scan.tag_id == models.Tag.id).join(models.Product,
                                                                                           models.Tag.product_id == models.Product.id).where(
        models.Product.manufacturer_id == current_user.id)

    if product_id:
        query = query.where(models.Product.id == product_id)
        # Verify product ownership
        product_query = await db.execute(
            select(models.Product).where(
                models.Product.id == product_id,
                models.Product.manufacturer_id == current_user.id
            )
        )
        if not product_query.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or not owned")

    if date_filter.start_date:
        query = query.where(models.Scan.timestamp >= date_filter.start_date)
    if date_filter.end_date:
        query = query.where(models.Scan.timestamp <= date_filter.end_date)

    query = query.order_by(models.Scan.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    scans = result.scalars().all()

    return [schemas.ScanResponse.from_orm(s) for s in scans]