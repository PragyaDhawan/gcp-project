from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional

class CreateRequest(BaseModel):
    github_url: HttpUrl
    prompt: str
    metadata: Optional[Dict[str, Any]] = None