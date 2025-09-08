"""
Pydantic schemas for dashboard analytics filters.
"""

from pydantic import BaseModel, validator
from datetime import datetime

class DateFilter(BaseModel):
    """
    Date range filter for dashboard analytics.

    Attributes:
        start_date (datetime): Start of date range.
        end_date (datetime): End of date range.
    """
    start_date: datetime | None = None
    end_date: datetime | None = None

    @validator('end_date')
    def validate_date_range(cls, end_date, values):
        """
        Ensures end_date is after start_date.
        """
        if end_date and 'start_date' in values and values['start_date'] and end_date < values['start_date']:
            raise ValueError("end_date must be after start_date")
        return end_date
