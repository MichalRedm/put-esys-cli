from typing import List

from pydantic import BaseModel


class SubmittedFile(BaseModel):
    name: str
    url: str


class AssignmentRow(BaseModel):
    key: str
    value: str
    files: List[SubmittedFile]


class AssignmentInfo(BaseModel):
    id: str
    title: str
    intro: str
    tables: List[List[AssignmentRow]]
