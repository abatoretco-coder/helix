from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    url: Optional[str]
    query: Optional[str]
    country: Optional[str]
    language: Optional[str]
    category: Optional[str]
    priority: int
    refresh_minutes: int
    enabled: bool
    last_checked_at: Optional[datetime]
    last_success_at: Optional[datetime]
    error_count: int


class SourceCreate(BaseModel):
    name: str
    source_type: str
    url: Optional[str] = None
    query: Optional[str] = None
    country: Optional[str] = None
    language: str = "en"
    category: str = "general"
    priority: int = 3
    refresh_minutes: int = 60
    extraction_strategy: str = "article"
    enabled: bool = True


class SourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    refresh_minutes: Optional[int] = None
    category: Optional[str] = None
