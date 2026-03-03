import os
import logging
from typing import Dict, Any
import ssl
import certifi
import dns.resolver
from google.cloud import secretmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Optional: secret manager client if you use Secret Manager
from google.cloud import secretmanager
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mongo Atlas API")

@app.get("/")
async def root():
    return {"status": "ok", "message": "API is running. See /docs for interactive API docs."}

def get_mongo_uri_from_secret_manager(secret_name: str) -> str | None:
    """
    Read the latest secret version from Secret Manager.
    secret_name format: projects/PROJECT_ID/secrets/SECRET_NAME
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=f"{secret_name}/versions/latest")
        payload = response.payload.data.decode("UTF-8")
        return payload
    except Exception as e:
        logger.warning("Secret Manager read failed: %s", e)
        return None

def get_mongo_uri() -> str:
    # 1) Prefer explicit env var (convenient)
    uri = os.environ.get("MONGO_URI")
    if uri:
        logger.info("Using MONGO_URI from environment")
        return uri

    # 2) Fall back to Secret Manager if env var absent.
    secret_env = os.environ.get("MONGO_SECRET_RESOURCE")  # e.g. projects/12345/secrets/mongo-uri
    if secret_env:
        secret_val = get_mongo_uri_from_secret_manager(secret_env)
        if secret_val:
            logger.info("Using MONGO_URI from Secret Manager")
            return secret_val

    raise RuntimeError("Mongo connection string not found. Set MONGO_URI or MONGO_SECRET_RESOURCE.")

# Create a global client lazily
_mongo_client: MongoClient | None = None
def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        uri = get_mongo_uri()
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Basic connectivity check
        _mongo_client.admin.command("ping")
        logger.info("Connected to MongoDB")
    return _mongo_client

class CreateDBRequest(BaseModel):
    db_name: str
    collection_name: str = "default_collection"
    initial_document: Dict[str, Any] | None = None

@app.post("/create-db")
def create_db(req: CreateDBRequest):
    """
    Create a database + collection by inserting an initial document.
    MongoDB creates DB/collection on first write.
    """
    try:
        client = get_mongo_client()
        db = client[req.db_name]
        coll = db[req.collection_name]
        doc = req.initial_document or {"created_by": "api", "note": "initial doc"}
        result = coll.insert_one(doc)
        return {"ok": True, "inserted_id": str(result.inserted_id)}
    except PyMongoError as e:
        logger.exception("Mongo error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("General error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/{db_name}/{collection_name}")
def read_all(db_name: str, collection_name: str, limit: int = 10):
    try:
        client = get_mongo_client()
        coll = client[db_name][collection_name]
        docs = list(coll.find({}, {"_id": 0}).limit(limit))
        return {"count": len(docs), "docs": docs}
    except PyMongoError as e:
        logger.exception("Mongo error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    # Lightweight health endpoint used by GAE
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        return {"status": "ok"}
    except Exception as e:
        logger.exception("health check failed")
        raise HTTPException(status_code=500, detail="db unavailable")
    
@app.get("/debug-tls")
def debug_tls():
    info = {}
    try:
        info['OPENSSL_VERSION'] = ssl.OPENSSL_VERSION
    except Exception as e:
        info['OPENSSL_VERSION'] = f"error: {e!r}"

    try:
        info['certifi_where'] = certifi.where()
    except Exception as e:
        info['certifi_where'] = f"error: {e!r}"

    # print PyMongo version if available
    try:
        import pymongo
        info['pymongo_version'] = pymongo.__version__
    except Exception:
        info['pymongo_version'] = "not installed"

    # show secret manager read (masked length)
    try:
        secret_env = os.environ.get("MONGO_SECRET_RESOURCE")
        if secret_env:
            client = secretmanager.SecretManagerServiceClient()
            resp = client.access_secret_version(name=f"{secret_env}/versions/latest")
            payload = resp.payload.data.decode("utf-8")
            info['secret_length'] = len(payload)
            info['secret_preview'] = payload[:16] + "..." if len(payload) > 16 else payload
        else:
            info['secret_length'] = None
            info['secret_preview'] = None
    except Exception as e:
        info['secret_error'] = repr(e)

    # show SRV resolution attempt (may fail if DNS blocked)
    try:
        answers = dns.resolver.resolve("_mongodb._tcp.mongodb-cluster0.scratcu.mongodb.net", "SRV")
        info['srv_records'] = [str(r) for r in answers]
    except Exception as e:
        info['srv_error'] = repr(e)

    return info

@app.route("/egress-ip")
def egress_ip():
    response = requests.get("https://ifconfig.me/ip")
    return response.text.strip()