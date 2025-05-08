# app/repository.py
from app.models import seo_analysis_collection


def create_seo_scan(scan_id: str, url: str):
    scan = {
        "_id": scan_id,
        "url": url,
        "status": "pending",
        "result": None
    }
    seo_analysis_collection.insert_one(scan)
    return scan


def get_seo_scan_by_id(scan_id: str):
    return seo_analysis_collection.find_one({"_id": scan_id})


def update_seo_scan_status(scan_id: str, status: str):
    seo_analysis_collection.update_one(
        {"_id": scan_id},
        {"$set": {"status": status}}
    )


def update_seo_scan_result(scan_id: str, result: dict):
    seo_analysis_collection.update_one(
        {"_id": scan_id},
        {"$set": {"result": result}}
    )