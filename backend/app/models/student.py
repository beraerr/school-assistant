"""
Student model
"""
import sys
import os
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import Base


class Student(Base):
    """Student model"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)  # e.g., "9-A", "10-B"
    total_absences = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Parent user ID
    
    # Relationships
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Student(name={self.name}, class={self.class_name})>"
