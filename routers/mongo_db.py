from datetime import datetime

from fastapi import APIRouter, HTTPException
from models.mongo import CreateRequest
from providers.mongo_provider import get_collection, get_mongo_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database", tags=["Mongo Database Operations"])

@router.get("/health")
def health():
    # Lightweight health endpoint used by GAE
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        return {"status": "ok"}
    except Exception as e:
        logger.exception("health check failed")
        raise HTTPException(status_code=500, detail="db unavailable")

@router.post("/create")
def create_issue(payload: CreateRequest):
    coll = get_collection()
    doc = {
        "github_url": str(payload.github_url),
        "prompt": payload.prompt,
        "metadata": payload.metadata or {},
        # store UTC datetime (MongoDB will keep it as a BSON datetime)
        "created_at": datetime.utcnow()
    }
    try:
        res = coll.insert_one(doc)
        return {"inserted_id": str(res.inserted_id)}
    except Exception as e:
        logger.exception("Failed to insert document")
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")