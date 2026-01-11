"""
Database models
"""
from .user import User
from .student import Student
from .teacher import Teacher
from .grade import Grade
from .attendance import Attendance

__all__ = [
    "User",
    "Student",
    "Teacher",
    "Grade",
    "Attendance",
]
