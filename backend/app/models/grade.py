"""
Grade model
"""
import sys
import os
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import Base


class Grade(Base):
    """Grade model"""
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String, nullable=False)  # e.g., "Matematik", "Fizik"
    grade = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="grades")
    
    def __repr__(self):
        return f"<Grade(student_id={self.student_id}, subject={self.subject}, grade={self.grade})>"
