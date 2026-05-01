"""
One-time migration from the original Access database to SQLite.

Prerequisites:
  - Microsoft Access Database Engine drivers installed
    (download: https://www.microsoft.com/en-us/download/details.aspx?id=54920)
  - pyodbc installed: pip install pyodbc
  - Run AFTER seed_data.py has populated reference tables

Usage:
    cd abetfac
    python -c "
    from app import create_app
    from migrations.migrate_from_access import migrate
    app = create_app()
    with app.app_context():
        migrate(r'C:\\path\\to\\ABET Assessments - Original - Full Artifact & Rubric Assessment - LOCK ENTRY.accdb')
    "
"""

import os
import shutil
import re
import pyodbc
from datetime import datetime, timezone

from app import db
from app.models import (Faculty, Semester, Student, Course, Enrollment,
                        AssessmentBatch, AssessmentDetail)

ACCESS_SCORE_MAP = {
    'Organization': 'score_organization',
    'Formatting': 'score_formatting',
    'Content': 'score_content',
    'References': 'score_references',
    'Graphical_Communication': 'score_graphical_comm',
    'Conduct_Safe_Lab_Experiments': 'score_safe_lab',
    'Analyze&Interpret_Data_w_Uncertainty': 'score_data_analysis',
    'Draw_Engineering_Conclusions': 'score_eng_conclusions',
}


def migrate(accdb_path, upload_root=None):
    """Migrate all data from the Access .accdb file into the SQLite database."""
    if not os.path.exists(accdb_path):
        raise FileNotFoundError(f'Access database not found: {accdb_path}')

    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={accdb_path};'
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print(f'Connected to Access DB: {accdb_path}')

    _migrate_semesters(cursor)
    _migrate_students(cursor)
    _migrate_enrollments(cursor)
    _migrate_batches_and_details(cursor, accdb_path, upload_root)
    _migrate_faculty_from_batches(cursor)

    conn.close()
    db.session.commit()
    print('\nMigration complete.')


def _migrate_semesters(cursor):
    print('Migrating semesters...')
    try:
        cursor.execute('SELECT Semesters FROM Semesters')
        for row in cursor.fetchall():
            label = str(row[0]).strip()
            parts = label.split()
            if len(parts) == 2:
                try:
                    year = int(parts[0])
                    term = parts[1]
                    if not Semester.query.filter_by(label=label).first():
                        is_active = (label == '2026 Spring')
                        db.session.add(Semester(label=label, year=year,
                                                term=term, is_active=is_active))
                except ValueError:
                    pass
        db.session.flush()
    except Exception as e:
        print(f'  Skipping semesters: {e}')


def _migrate_students(cursor):
    print('Migrating students...')
    seen = set()
    for table in ('tblStudents', '2026_Spring_Courses'):
        try:
            cursor.execute(f'SELECT * FROM [{table}]')
            cols = [d[0] for d in cursor.description]
            for row in cursor.fetchall():
                r = dict(zip(cols, row))
                elearn = str(r.get('ELEARN_ID', '') or '').strip()
                first = str(r.get('Student_First', '') or '').strip()
                last = str(r.get('Student_Last', '') or '').strip()
                if elearn and first and last and elearn not in seen:
                    seen.add(elearn)
                    if not Student.query.filter_by(elearn_id=elearn).first():
                        db.session.add(Student(elearn_id=elearn,
                                               first_name=first, last_name=last))
        except Exception as e:
            print(f'  Skipping {table}: {e}')
    db.session.flush()
    print(f'  {len(seen)} students processed.')


def _migrate_enrollments(cursor):
    print('Migrating enrollments...')
    added = 0
    try:
        cursor.execute('SELECT * FROM [2026_Spring_Courses]')
        cols = [d[0] for d in cursor.description]
        sem = Semester.query.filter_by(label='2026 Spring').first()
        for row in cursor.fetchall():
            r = dict(zip(cols, row))
            elearn = str(r.get('ELEARN_ID', '') or '').strip()
            course_id = str(r.get('Course', '') or '').strip().upper()
            if not elearn or not course_id or not sem:
                continue
            student = Student.query.filter_by(elearn_id=elearn).first()
            course = Course.query.get(course_id)
            if not student or not course:
                continue
            if not Enrollment.query.filter_by(student_id=student.id,
                                               course_id=course_id,
                                               semester_id=sem.id).first():
                db.session.add(Enrollment(student_id=student.id,
                                          course_id=course_id,
                                          semester_id=sem.id))
                added += 1
        db.session.flush()
    except Exception as e:
        print(f'  Skipping enrollments: {e}')
    print(f'  {added} enrollment records added.')


def _migrate_batches_and_details(cursor, accdb_path, upload_root):
    from app.models import SLO
    print('Migrating assessment batches and details...')

    # Map faculty last name -> Faculty record (create if needed)
    faculty_map = {}

    def get_faculty(last_name):
        last_name = (last_name or '').strip()
        if not last_name:
            return None
        if last_name in faculty_map:
            return faculty_map[last_name]
        username = re.sub(r'[^a-z0-9]', '', last_name.lower())
        user = Faculty.query.filter_by(username=username).first()
        if not user:
            user = Faculty(username=username,
                           display_name=f'Dr. {last_name}',
                           force_password_reset=True)
            user.set_password('changeme123')
            db.session.add(user)
            db.session.flush()
            print(f'  Created faculty: {username} (display: Dr. {last_name})')
        faculty_map[last_name] = user
        return user

    try:
        cursor.execute('SELECT * FROM tblAssessmentBatch')
        batch_cols = [d[0] for d in cursor.description]
        for row in cursor.fetchall():
            b = dict(zip(batch_cols, row))
            access_batch_id = b['AssessmentBatch_ID']
            course_id = str(b.get('Course_ID', '') or '').strip().upper()
            faculty_last = str(b.get('Faculty_Last', '') or '').strip()
            sem_label = str(b.get('Semester_Assessed', '') or '').strip()

            if not course_id:
                continue

            course = Course.query.get(course_id)
            if not course:
                print(f'  Batch {access_batch_id}: course {course_id} not found, skipping.')
                continue

            sem = Semester.query.filter_by(label=sem_label).first()
            if not sem:
                # Try to create it
                parts = sem_label.split()
                if len(parts) == 2:
                    try:
                        sem = Semester(label=sem_label, year=int(parts[0]), term=parts[1])
                        db.session.add(sem)
                        db.session.flush()
                    except Exception:
                        sem = Semester.query.filter_by(is_active=True).first()

            faculty = get_faculty(faculty_last)
            if not faculty:
                continue

            # Pick first SLO mapped to course as default
            from app.models import CourseSLO
            cs = CourseSLO.query.filter_by(course_id=course_id).first()
            slo_id = cs.slo_id if cs else SLO.query.first().id

            batch = AssessmentBatch(
                course_id=course_id,
                faculty_id=faculty.id,
                semester_id=sem.id if sem else 1,
                slo_id=slo_id,
                action_taken='Evaluation',
            )
            db.session.add(batch)
            db.session.flush()

            # Migrate details for this batch
            _migrate_batch_details(cursor, access_batch_id, batch, accdb_path, upload_root)

    except Exception as e:
        print(f'  Error migrating batches: {e}')

    db.session.flush()


def _migrate_batch_details(cursor, access_batch_id, new_batch, accdb_path, upload_root):
    try:
        cursor.execute(
            'SELECT * FROM tblAssessmentDetail WHERE AssessmentBatch_ID = ?',
            access_batch_id
        )
        cols = [d[0] for d in cursor.description]
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            elearn = str(d.get('ELEARN_ID', '') or '').strip()
            if not elearn:
                continue

            student = Student.query.filter_by(elearn_id=elearn).first()
            if not student:
                first = str(d.get('Student_First', '') or 'Unknown').strip()
                last = str(d.get('Student_Last', '') or 'Unknown').strip()
                student = Student(elearn_id=elearn, first_name=first, last_name=last)
                db.session.add(student)
                db.session.flush()

            detail = AssessmentDetail(
                batch_id=new_batch.id,
                student_id=student.id,
                earned_grade=str(d.get('Earned_Grade', '') or '').strip() or None,
            )

            for access_col, model_field in ACCESS_SCORE_MAP.items():
                val = d.get(access_col)
                if val is not None:
                    try:
                        score = int(float(val))
                        if 1 <= score <= 4:
                            setattr(detail, model_field, score)
                    except (TypeError, ValueError):
                        pass

            # Handle artifact path
            artifact_path = str(d.get('Artifact', '') or '').strip()
            if artifact_path and upload_root:
                if os.path.exists(artifact_path):
                    sem_label = new_batch.semester.label.replace(' ', '_')
                    course_safe = new_batch.course_id.replace(' ', '')
                    dest_dir = os.path.join(upload_root, sem_label, course_safe,
                                            f'batch_{new_batch.id}')
                    os.makedirs(dest_dir, exist_ok=True)
                    filename = os.path.basename(artifact_path)
                    dest = os.path.join(dest_dir, filename)
                    try:
                        shutil.copy2(artifact_path, dest)
                        detail.artifact_path = os.path.relpath(dest, upload_root)
                        detail.artifact_filename = filename
                    except Exception as copy_err:
                        print(f'    Could not copy artifact {artifact_path}: {copy_err}')

            db.session.add(detail)

    except Exception as e:
        print(f'  Error migrating details for batch {access_batch_id}: {e}')


def _migrate_faculty_from_batches(cursor):
    """Ensure any faculty names in legacy tables get accounts."""
    pass  # Already handled in _migrate_batches_and_details
