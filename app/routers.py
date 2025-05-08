# app/routes.py
from fastapi import APIRouter, HTTPException
from typing import Any

from app.seo_service import SEOService
from app.schemas import AnalysisRequest, AnalysisResponse
from app.logger_config import logger

router = APIRouter()
seo_service = SEOService()


@router.post("/start-analysis/", response_model=AnalysisResponse)
def start_analysis(request: AnalysisRequest) -> AnalysisResponse:
    logger.info(f"Received request to start SEO analysis for URL: {request.url}")
    try:
        scan = seo_service.start_seo_analysis(url=request.url)
        scan["id"] = scan.pop("_id")  # Fix FastAPI validation issue
        return AnalysisResponse(**scan)
    except ValueError as ve:
        logger.warning(f"Invalid URL format for URL: {request.url}. Error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error starting analysis for URL: {request.url}. Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/get-analysis/{scan_id}", response_model=AnalysisResponse)
def get_analysis(scan_id: str) -> AnalysisResponse:
    logger.info(f"Fetching SEO analysis for scan ID: {scan_id}")
    try:
        scan = seo_service.get_seo_analysis(scan_id=scan_id)
        scan["id"] = scan.pop("_id")  # Fix FastAPI validation issue
        return AnalysisResponse(**scan)
    except Exception as e:
        logger.warning(f"Scan with ID {scan_id} not found. Error: {str(e)}")
        raise HTTPException(status_code=404, detail="Scan not found")