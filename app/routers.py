from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.models import seo_analysis_collection
from app.tasks import perform_seo_analysis
from app.logger_config import logger
import uuid

router = APIRouter()

class AnalysisRequest(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    id: str
    status: str
    result: Optional[Dict] = None

@router.post("/start-analysis/", response_model=AnalysisResponse)
def start_analysis(request: AnalysisRequest):
    scan_id = str(uuid.uuid4())
    scan = {
        "_id": scan_id,
        "url": request.url,
        "status": "pending",
        "result": None
    }
    try:
        seo_analysis_collection.insert_one(scan)
        logger.info(f"Scan object inserted with ID: {scan_id}")
    except Exception as e:
        logger.error(f"Error inserting scan object: {e}")
        raise HTTPException(status_code=500, detail="Error inserting scan object")

    perform_seo_analysis.delay(scan_id, request.url)

    return AnalysisResponse(
        id=scan["_id"],
        status=scan["status"],
        result=scan["result"]
    )

@router.get("/get-analysis/{scan_id}", response_model=AnalysisResponse)
def get_analysis(scan_id: str):
    logger.info(f"Fetching scan details for scan ID: {scan_id}")
    scan = seo_analysis_collection.find_one({"_id": scan_id})
    if not scan:
        logger.warning(f"Scan with ID {scan_id} not found")
        raise HTTPException(status_code=404, detail="Scan not found")

    return AnalysisResponse(
        id=scan["_id"],
        status=scan["status"],
        result=scan["result"]
    )