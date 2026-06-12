from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ClusterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    main_title: Optional[str]
    main_summary: Optional[str]
    topic: Optional[str]
    language: Optional[str]
    article_count: int
    importance_score: Optional[float]
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]


class ClusterDetail(BaseModel):
    cluster: ClusterRead
    articles: list[Any]  # ArticleRead — avoid circular import
