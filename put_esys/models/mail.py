from typing import List, Optional

from pydantic import BaseModel


class EmailSummary(BaseModel):
    id: str
    subject: str
    from_: str  # maps to from in raw dict
    to: Optional[str] = None
    date: Optional[str] = None


class EmailDetails(BaseModel):
    id: str
    subject: str
    from_: str
    to: Optional[str] = None
    date: Optional[str] = None
    body: str
    attachments: List[str]
