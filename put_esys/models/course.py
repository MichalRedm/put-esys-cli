from enum import Enum
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


class CourseCategory(BaseModel):
    id: str
    name: str
    url: str
    course_count: Optional[int] = None


class DiscoveredCourse(BaseModel):
    id: str
    title: str
    url: str
    category_name: Optional[str] = None
    requires_key: bool = False
    summary: Optional[str] = None


class CategoryBrowseResult(BaseModel):
    current_category: Optional[CourseCategory] = None
    subcategories: List[CourseCategory] = []
    courses: List[DiscoveredCourse] = []


class EnrolmentStatus(str, Enum):
    ALREADY_ENROLLED = "already_enrolled"
    CAN_ENROL = "can_enrol"
    CAN_ENROL_KEY_REQUIRED = "can_enrol_key_required"
    NO_SELF_ENROLMENT = "no_self_enrolment"


class EnrolmentInfo(BaseModel):
    course_id: str
    course_title: str
    status: EnrolmentStatus
    requires_password: bool = False
    instance_id: Optional[str] = None
    sesskey: Optional[str] = None
    error_message: Optional[str] = None


class CourseContent(BaseModel):
    title: str
    sections: List[Section]

