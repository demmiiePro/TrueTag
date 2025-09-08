from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TagBase(BaseModel):
    tag_code: str
    token_id: str
    status: Optional[str] = "unused"

class TagCreate(TagBase):
    product_id: int

class TagResponse(TagBase):
    id: int
    blockchain_tx_hash: Optional[str] = None
    product_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class TagGenerationRequest(BaseModel):
    product_id: Optional[int] = None
    count: int
    mint_type: str  # "warehouse" or "direct"

class TagGenerationResponse(BaseModel):
    message: str
    assigned_tag_codes: Optional[List[str]] = None
