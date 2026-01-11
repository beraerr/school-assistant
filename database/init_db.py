"""
Database initialization script with sample data
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.user import User, UserRole
from backend.app.models.student import Student
from backend.app.models.teacher import Teacher
from backend.app.models.grade import Grade
from backend.app.models.attendance import Attendance
from backend.app.core.security import get_password_hash
from datetime import date, timedelta
import random

def create_sample_data():
    """Create sample data for testing"""
    db: Session = SessionLocal()
    
    try:
        # Clear existing data
        db.query(Attendance).delete()
        db.query(Grade).delete()
        db.query(Student).delete()
        db.query(Teacher).delete()
        db.query(User).delete()
        db.commit()
        
        # Create Teachers
        teacher1 = Teacher(name="Ahmet Öğretmen", class_name="9-A")
        teacher2 = Teacher(name="Ayşe Öğretmen", class_name="10-B")
        db.add(teacher1)
        db.add(teacher2)
        db.flush()
        
        # Create Students
        students_data = [
            {"name": "Ali Yılmaz", "class_name": "9-A", "total_absences": 3},
            {"name": "Zeynep Demir", "class_name": "9-A", "total_absences": 7},
            {"name": "Mehmet Kaya", "class_name": "9-A", "total_absences": 2},
            {"name": "Elif Şahin", "class_name": "10-B", "total_absences": 1},
            {"name": "Can Arslan", "class_name": "10-B", "total_absences": 6},
            {"name": "Selin Yıldız", "class_name": "10-B", "total_absences": 4},
        ]
        
        students = []
        for data in students_data:
            student = Student(**data)
            db.add(student)
            students.append(student)
        
        db.flush()
        
        # Create Users
        # Principal
        principal_user = User(
            username="principal",
            password_hash=get_password_hash("admin123"),
            role=UserRole.PRINCIPAL,
            related_id=None,
            related_class=None
        )
        db.add(principal_user)
        
        # Teachers
        teacher1_user = User(
            username="teacher1",
            password_hash=get_password_hash("teacher123"),
            role=UserRole.TEACHER,
            related_id=teacher1.id,
            related_class="9-A"
        )
        teacher2_user = User(
            username="teacher2",
            password_hash=get_password_hash("teacher123"),
            role=UserRole.TEACHER,
            related_id=teacher2.id,
            related_class="10-B"
        )
        db.add(teacher1_user)
        db.add(teacher2_user)
        
        # Parents (for first 3 students)
        parent1_user = User(
            username="parent1",
            password_hash=get_password_hash("parent123"),
            role=UserRole.PARENT,
            related_id=students[0].id,
            related_class=None
        )
        parent2_user = User(
            username="parent2",
            password_hash=get_password_hash("parent123"),
            role=UserRole.PARENT,
            related_id=students[1].id,
            related_class=None
        )
        db.add(parent1_user)
        db.add(parent2_user)
        
        # Students
        student1_user = User(
            username="student1",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            related_id=students[0].id,
            related_class=None
        )
        student2_user = User(
            username="student2",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            related_id=students[1].id,
            related_class=None
        )
        db.add(student1_user)
        db.add(student2_user)
        
        db.flush()
        
        # Update students with parent_id
        students[0].parent_id = parent1_user.id
        students[1].parent_id = parent2_user.id
        
        # Create Grades
        subjects = ["Matematik", "Fizik", "Kimya", "Türkçe", "Tarih"]
        today = date.today()
        
        for student in students:
            for subject in subjects:
                # Create grades for last 3 months
                for month_offset in range(3):
                    grade_date = today - timedelta(days=30 * month_offset)
                    grade = Grade(
                        student_id=student.id,
                        subject=subject,
                        grade=round(random.uniform(50, 100), 2),
                        date=grade_date
                    )
                    db.add(grade)
        
        # Create Attendance records
        # Create attendance for last 30 days
        for day_offset in range(30):
            attendance_date = today - timedelta(days=day_offset)
            for student in students:
                # Random attendance status
                statuses = ["present", "present", "present", "present", "absent", "excused"]
                status = random.choice(statuses)
                
                attendance = Attendance(
                    student_id=student.id,
                    date=attendance_date,
                    status=status
                )
                db.add(attendance)
        
        db.commit()
        print("Sample data created successfully!")
        print("\nDemo Users:")
        print("  Principal: principal / admin123")
        print("  Teacher 1: teacher1 / teacher123 (9-A)")
        print("  Teacher 2: teacher2 / teacher123 (10-B)")
        print("  Parent 1: parent1 / parent123 (Ali Yılmaz)")
        print("  Parent 2: parent2 / parent123 (Zeynep Demir)")
        print("  Student 1: student1 / student123 (Ali Yılmaz)")
        print("  Student 2: student2 / student123 (Zeynep Demir)")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Creating sample data...")
    create_sample_data()
