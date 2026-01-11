"""
Teacher model
"""
import sys
import os
from sqlalchemy import Column, Integer, String

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import Base


class Teacher(Base):
    """Teacher model"""
    __tablename__ = "teachers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)  # Assigned class
    
    def __repr__(self):
        return f"<Teacher(name={self.name}, class={self.class_name})>"
