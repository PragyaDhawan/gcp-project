# Optional: secret manager client if you use Secret Manager
from google.cloud import secretmanager
from datetime import datetime
import logging
import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from constants import DB_NAME, COLLECTION_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    # Secret Manager
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


def get_collection():
    """Get the collection object (lazy client creation delegated to your helper)."""
    client = get_mongo_client()
    db = client[DB_NAME]
    coll = db[COLLECTION_NAME]
    # ensure a couple useful indexes (idempotent)
    try:
        coll.create_index("github_url")
        coll.create_index("created_at")
    except Exception as e:
        logger.debug("Index creation skipped/failed: %s", e)
    return coll