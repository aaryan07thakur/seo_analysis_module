from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.models import seo_analysis_collection
from app.tasks import perform_seo_analysis
import uuid
from typing import Optional, Dict

app = FastAPI()

class AnalysisRequest(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    id: str
    status: str
    result: Optional[Dict] = None  # Default value is None

@app.post("/start-analysis/", response_model=AnalysisResponse)
def start_analysis(request: AnalysisRequest):
    # Generate a unique scan ID
    scan_id = str(uuid.uuid4())

    # Create a new scan object
    scan = {
        "_id": scan_id,
        "url": request.url,
        "status": "pending",
        "result": None  # Explicitly set result to None
    }
    seo_analysis_collection.insert_one(scan)

    # Trigger Celery task
    perform_seo_analysis.delay(scan_id, request.url)

    # Return the response with the correct fields
    return AnalysisResponse(
        id=scan["_id"],  # Explicitly map the `_id` field to `id`
        status=scan["status"],
        result=scan["result"]  # Explicitly set `result` to `None`
    )

@app.get("/get-analysis/{scan_id}", response_model=AnalysisResponse)
def get_analysis(scan_id: str):
    scan = seo_analysis_collection.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Return the response with the correct fields
    return AnalysisResponse(
        id=scan["_id"],
        status=scan["status"],
        result=scan["result"]  # This will be `None` initially and updated later
    )