from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BriefingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: str
    period_date: datetime
    category: str
    content: Optional[str]
    article_ids: Optional[list[int]]
    generated_at: datetime
