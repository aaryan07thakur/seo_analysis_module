from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.models import seo_analysis_collection
from app.tasks import perform_seo_analysis
from app.logger_config import logger
import uuid

router = APIRouter()


#Data models

class AnalysisRequest(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    id: str
    url:str
    status: str
    result: Optional[Dict] = None

@router.post("/start-analysis/", response_model=AnalysisResponse)  #PosT Endpoints
def start_analysis(request: AnalysisRequest):
    scan_id = str(uuid.uuid4())      #Generates unique id for the analysis
    scan = {         #creates a dictionary to store in the data base
        "_id": scan_id,
        "url": request.url,
        "status": "pending",
        "result": None
    }
    try:
        seo_analysis_collection.insert_one(scan)  # try to store in db if successful it logs
        logger.info(f"Scan object inserted with ID: {scan_id}")
    except Exception as e:        
        logger.error(f"Error inserting scan object: {e}")  #if error occures then shows 500 internal server error
        raise HTTPException(status_code=500, detail="Error inserting scan object")

    perform_seo_analysis.delay(scan_id, request.url)   # with the help of delay call the background task asynchronously

    return AnalysisResponse(
        url=scan["url"],
        id=scan["_id"],
        status=scan["status"],
        result=scan["result"]
    )

@router.get("/get-analysis/{scan_id}", response_model=AnalysisResponse)    # creating GET endpoints
def get_analysis(scan_id: str): 
    logger.info(f"Fetching scan details for scan ID: {scan_id}")  # shows logs fetching scan details
    scan = seo_analysis_collection.find_one({"_id": scan_id})  # search for the scan in db
    if not scan:
        logger.warning(f"Scan with ID {scan_id} not found")   #if not found the shows logs warning and 404 not found
        raise HTTPException(status_code=404, detail="Scan not found")

    return AnalysisResponse(         # if scan found then return analysis details
         url=scan["url"],
        id=scan["_id"],
        status=scan["status"],
        result=scan["result"]
    )