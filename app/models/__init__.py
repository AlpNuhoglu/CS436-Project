"""
SQLAlchemy ORM modelleri.

Tüm modeller burada import edilerek dışa açılır.
Alembic'in otomatik migration üretebilmesi için bu modüle erişmesi yeterlidir.
"""
from app.models.user import User
from app.models.pending_registration import PendingRegistration
from app.models.password_reset_request import PasswordResetRequest
from app.models.pending_email_bind import PendingEmailBind
from app.models.professor import Professor
from app.models.course import Course
from app.models.professor_course import ProfessorCourse
from app.models.review import Review
from app.models.upvote import Upvote
from app.models.downvote import Downvote

__all__ = [
    "User",
    "PendingRegistration",
    "PasswordResetRequest",
    "PendingEmailBind",
    "Professor",
    "Course",
    "ProfessorCourse",
    "Review",
    "Upvote",
    "Downvote",
]
