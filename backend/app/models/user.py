"""
User model for authentication and role management
"""
import sys
import os
from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles"""
    PRINCIPAL = "principal"
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    related_id = Column(Integer, nullable=True)  # student_id for parent/student, teacher_id for teacher
    related_class = Column(String, nullable=True)  # class name for teacher
    
    # Relationships
    student = relationship("Student", foreign_keys="Student.id", uselist=False, 
                          primaryjoin="and_(User.related_id==Student.id, User.role=='student')")
    teacher = relationship("Teacher", foreign_keys="Teacher.id", uselist=False,
                          primaryjoin="and_(User.related_id==Teacher.id, User.role=='teacher')")
    
    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"
