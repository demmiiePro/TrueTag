from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class BatchCreate(BaseModel):
    product_id: Optional[int] = None
    count: int
    mint_type: str  # "warehouse" or "direct"

class BatchResponse(BaseModel):
    id: int
    product_id: Optional[int]
    count: int
    status: str
    mint_type: str
    blockchain_tx_hash: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BatchAssignmentResponse(BaseModel):
    message: str
    assigned_tag_codes: List[str]
