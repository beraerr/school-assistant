"""
Attendance model
"""
import sys
import os
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import Base


class Attendance(Base):
    """Attendance model"""
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # "present", "absent", "excused"
    
    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    
    def __repr__(self):
        return f"<Attendance(student_id={self.student_id}, date={self.date}, status={self.status})>"
