from typing import List, Optional

from pydantic import BaseModel


class Attachment(BaseModel):
    name: str
    url: str


class Question(BaseModel):
    number: str
    state: str
    type: str
    allows_attachments: bool
    text: str  # HTML
    answer: str  # HTML
    attachments: List[Attachment]


class QuizAttemptSummary(BaseModel):
    number: Optional[str] = None
    id: Optional[str] = None
    status: Optional[str] = None
    started: Optional[str] = None
    grade: Optional[str] = None
    review_url: Optional[str] = None


class QuizActionButton(BaseModel):
    text: str
    url: str


class QuizInfo(BaseModel):
    title: str
    intro: str
    info: List[str]
    grading_method: str
    attempts: List[QuizAttemptSummary]
    buttons: List[QuizActionButton]
    sesskey: Optional[str] = None


class QuizAttemptDetails(BaseModel):
    quiz_id: int
    attempt_id: int
    questions: List[Question]
