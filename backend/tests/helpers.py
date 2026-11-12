"""Shared test helper functions accessible by all test modules."""
from datetime import date


def _make_student(db, student_id):
    from app.models.student import Student
    if not db.query(Student).filter(Student.student_id == student_id).first():
        db.add(Student(student_id=student_id, first_name="Test", last_name="Student",
                        email=f"{student_id.lower().replace('-','.')}@test.com",
                        enrollment_date=date(2026, 1, 15), academic_year="2026",
                        department="Computer Science", program="B.Sc CS", current_status="ACTIVE"))
        db.commit()


def _make_course(db, course_id):
    from app.models.course import Course
    if not db.query(Course).filter(Course.course_id == course_id).first():
        db.add(Course(course_id=course_id, course_name="Test Course",
                       course_code=f"TC{course_id[-4:]}", department="Computer Science",
                       credits=3, semester="2026-S1"))
        db.commit()


def _make_enrollment(db, student_id, course_id, enrollment_id):
    from app.models.enrollment import Enrollment
    if not db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first():
        db.add(Enrollment(enrollment_id=enrollment_id, student_id=student_id,
                           course_id=course_id, enrollment_date=date(2026, 1, 15),
                           effective_from=date(2026, 1, 15), enrollment_status="ACTIVE"))
        db.commit()


def _make_attendance(db, enrollment_id, records):
    from app.models.attendance import AttendanceEvent
    for i, (d, status) in enumerate(records, 1):
        att_id = f"ATT-{enrollment_id}-{d.strftime('%Y%m%d')}-{i}"
        if not db.query(AttendanceEvent).filter(AttendanceEvent.attendance_id == att_id).first():
            db.add(AttendanceEvent(
                attendance_id=att_id, enrollment_id=enrollment_id,
                attendance_date=d, attendance_status=status, session_number=i,
            ))
    db.commit()

