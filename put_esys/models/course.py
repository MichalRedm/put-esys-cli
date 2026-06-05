from typing import List, Optional

from pydantic import BaseModel


class Activity(BaseModel):
    name: str
    url: Optional[str] = None
    type: str
    content: Optional[str] = None
    children: Optional[List["Activity"]] = None


class Section(BaseModel):
    name: str
    activities: List[Activity]


class Course(BaseModel):
    id: str
    title: str
    url: str


class CourseContent(BaseModel):
    title: str
    sections: List[Section]
