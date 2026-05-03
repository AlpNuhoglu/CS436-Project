"""
Pydantic schemas - istek (request) ve yanıt (response) modelleri.

Her resource için iki temel schema tutulur:
- ...Create  (input)  -> POST/PUT body
- ...Read    (output) -> response model
"""
from app.schemas.professor import ProfessorCreate, ProfessorRead, ProfessorDetail, CourseInProfessor
from app.schemas.course import (
    CourseCreate,
    CourseRead,
    CourseListResponse,
    CourseDetail,
    ProfessorInCourse,
)

__all__ = [
    "ProfessorCreate", "ProfessorRead", "ProfessorDetail", "CourseInProfessor",
    "CourseCreate", "CourseRead", "CourseListResponse", "CourseDetail", "ProfessorInCourse",
]
