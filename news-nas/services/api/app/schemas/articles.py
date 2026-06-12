from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ArticleAIRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary_short: Optional[str]
    summary_long: Optional[str]
    category: Optional[str]
    topics: Optional[list[str]]
    entities: Optional[Any]
    sentiment: Optional[str]
    final_score: Optional[float]
    importance_score: Optional[float]
    novelty_score: Optional[float]
    personal_relevance_score: Optional[float]
    processed_at: Optional[datetime]


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    author: Optional[str]
    language: Optional[str]
    published_at: Optional[datetime]
    word_count: Optional[int]
    quality_score: Optional[float]
    extractor_used: Optional[str]
    source_id: Optional[int]
    ai: Optional[ArticleAIRead]


class ArticleDetail(ArticleRead):
    text_content: Optional[str]
    image_url: Optional[str]
    raw_html_path: Optional[str]
