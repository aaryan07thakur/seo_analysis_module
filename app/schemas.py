from pydantic import BaseModel
from typing import Optional, Dict

class AnalysisRequest(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    id: str  # Ensure this matches the type of `_id` in MongoDB
    status: str
    result: Optional[Dict] = None  # Allow `None` for the result field