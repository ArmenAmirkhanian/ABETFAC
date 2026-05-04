import csv
import io
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort)
from flask_login import login_required, current_user
from app import db
from app.models import (Faculty, Course, Program, Semester, Enrollment,
                        Student, SLO, CourseSLO, RubricCriterion)

admin_bp = Blueprint('admin', __name__)


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------
@admin_bp.route('/')
@login_required
def index():
    _require_admin()
    stats = {
        'users': Faculty.query.count(),
        'courses': Course.query.count(),
        'students': Student.query.count(),
        'semesters': Semester.query.count(),
    }
    active_sem = Semester.query.filter_by(is_active=True).first()
    return render_template('admin/dashboard.html', stats=stats, active_sem=active_sem)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
@admin_bp.route('/users')
@login_required
def users():
    _require_admin()
    all_users = Faculty.query.order_by(Faculty.display_name).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def user_new():
    _require_admin()
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip() or None
        password = request.form.get('password', '')
        is_admin = bool(request.form.get('is_admin'))

        if not username or not display_name or not password:
            error = 'Username, display name, and password are required.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif Faculty.query.filter_by(username=username).first():
            error = f'Username "{username}" is already taken.'
        else:
            user = Faculty(username=username, display_name=display_name,
                           email=email, is_admin=is_admin, force_password_reset=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'User "{display_name}" created. They will be prompted to change their password on first login.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', error=error, user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    _require_admin()
    user = Faculty.query.get_or_404(user_id)
    error = None

    if request.method == 'POST':
        user.display_name = request.form.get('display_name', '').strip()
        user.email = request.form.get('email', '').strip() or None
        user.is_admin = bool(request.form.get('is_admin'))

        new_password = request.form.get('new_password', '').strip()
        if new_password:
            if len(new_password) < 8:
                error = 'Password must be at least 8 characters.'
            else:
                user.set_password(new_password)
                user.force_password_reset = True

        if not error:
            db.session.commit()
            flash(f'User "{user.display_name}" updated.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', error=error, user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    _require_admin()
    user = Faculty.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
    else:
        name = user.display_name
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{name}" deleted.', 'info')
    return redirect(url_for('admin.users'))


# ---------------------------------------------------------------------------
# Course management
# ---------------------------------------------------------------------------
@admin_bp.route('/courses')
@login_required
def courses():
    _require_admin()
    all_courses = Course.query.order_by(Course.id).all()
    programs = Program.query.order_by(Program.code).all()
    return render_template('admin/courses.html', courses=all_courses, programs=programs)


@admin_bp.route('/courses/new', methods=['GET', 'POST'])
@login_required
def course_new():
    _require_admin()
    programs = Program.query.order_by(Program.code).all()
    slos = SLO.query.order_by(SLO.code).all()
    error = None

    if request.method == 'POST':
        course_id = request.form.get('id', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not course_id or not name:
            error = 'Course ID and name are required.'
        elif Course.query.get(course_id):
            error = f'Course "{course_id}" already exists.'
        else:
            course = Course(
                id=course_id, name=name,
                credit_hours=request.form.get('credit_hours', type=int),
                schedule_type=request.form.get('schedule_type', '').strip() or None,
                special_attributes=request.form.get('special_attributes', '').strip() or None,
                core_designations=request.form.get('core_designations', '').strip() or None,
            )
            program_ids = request.form.getlist('program_ids', type=int)
            course.programs = [Program.query.get(pid) for pid in program_ids if pid]
            db.session.add(course)
            db.session.flush()
            for slo_id in request.form.getlist('slo_ids', type=int):
                db.session.add(CourseSLO(course_id=course_id, slo_id=slo_id))
            db.session.commit()
            flash(f'Course {course_id} created.', 'success')
            return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', error=error,
                           course=None, programs=programs, slos=slos,
                           course_slo_ids=[])


@admin_bp.route('/courses/<course_id>/edit', methods=['GET', 'POST'])
@login_required
def course_edit(course_id):
    _require_admin()
    course = Course.query.get_or_404(course_id)
    programs = Program.query.order_by(Program.code).all()
    slos = SLO.query.order_by(SLO.code).all()
    error = None
    course_slo_ids = [cs.slo_id for cs in course.course_slos.all()]

    if request.method == 'POST':
        course.name = request.form.get('name', '').strip()
        course.credit_hours = request.form.get('credit_hours', type=int)
        course.schedule_type = request.form.get('schedule_type', '').strip() or None
        course.special_attributes = request.form.get('special_attributes', '').strip() or None
        course.core_designations = request.form.get('core_designations', '').strip() or None
        program_ids = request.form.getlist('program_ids', type=int)
        course.programs = [Program.query.get(pid) for pid in program_ids if pid]

        # Rebuild SLO mappings
        CourseSLO.query.filter_by(course_id=course_id).delete()
        for slo_id in request.form.getlist('slo_ids', type=int):
            db.session.add(CourseSLO(course_id=course_id, slo_id=slo_id))

        db.session.commit()
        flash(f'Course {course_id} updated.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', error=error,
                           course=course, programs=programs, slos=slos,
                           course_slo_ids=course_slo_ids)


# ---------------------------------------------------------------------------
# Semester management
# ---------------------------------------------------------------------------
@admin_bp.route('/semesters')
@login_required
def semesters():
    _require_admin()
    all_sems = Semester.query.order_by(Semester.year.desc(), Semester.term).all()
    return render_template('admin/semesters.html', semesters=all_sems)


@admin_bp.route('/semesters/new', methods=['POST'])
@login_required
def semester_new():
    _require_admin()
    year = request.form.get('year', type=int)
    term = request.form.get('term', '').strip()
    if year and term:
        label = f'{year} {term}'
        if not Semester.query.filter_by(label=label).first():
            db.session.add(Semester(label=label, year=year, term=term))
            db.session.commit()
            flash(f'Semester "{label}" added.', 'success')
        else:
            flash(f'Semester "{label}" already exists.', 'warning')
    return redirect(url_for('admin.semesters'))


@admin_bp.route('/semesters/<int:sem_id>/activate', methods=['POST'])
@login_required
def semester_activate(sem_id):
    _require_admin()
    Semester.query.update({'is_active': False})
    sem = Semester.query.get_or_404(sem_id)
    sem.is_active = True
    db.session.commit()
    flash(f'"{sem.label}" is now the active semester.', 'success')
    return redirect(url_for('admin.semesters'))


# ---------------------------------------------------------------------------
# Enrollment import
# ---------------------------------------------------------------------------
@admin_bp.route('/enrollments/import', methods=['GET', 'POST'])
@login_required
def import_enrollments():
    _require_admin()
    semesters_list = Semester.query.order_by(Semester.year.desc(), Semester.term).all()
    results = None

    if request.method == 'POST':
        sem_id = request.form.get('semester_id', type=int)
        sem = Semester.query.get(sem_id)
        if not sem:
            flash('Please select a semester.', 'danger')
            return render_template('admin/import.html', semesters=semesters_list)

        f = request.files.get('csv_file')
        if not f or not f.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return render_template('admin/import.html', semesters=semesters_list)

        stream = io.StringIO(f.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)

        added = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, 2):
            try:
                normalized = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
                elearn_id = normalized.get('elearn_id') or normalized.get('student_id') or normalized.get('studentid') or ''
                first = normalized.get('first_name') or normalized.get('student_first') or normalized.get('studentfirstname') or ''
                last = normalized.get('last_name') or normalized.get('student_last') or normalized.get('studentlastname') or ''
                student_major = normalized.get('student_major') or normalized.get('student major') or normalized.get('major') or ''
                course_id = (normalized.get('course_id') or normalized.get('course') or normalized.get('course id') or '').upper()

                if not all([elearn_id, first, last, student_major, course_id]):
                    errors.append(f'Row {i}: missing required field(s). Expected elearn_id, first_name, last_name, student_major, course_id.')
                    continue

                course = Course.query.get(course_id)
                if not course:
                    errors.append(f'Row {i}: course "{course_id}" not found.')
                    continue

                student = Student.query.filter_by(elearn_id=elearn_id).first()
                if not student:
                    student = Student(elearn_id=elearn_id, first_name=first, last_name=last, student_major=student_major)
                    db.session.add(student)
                    db.session.flush()
                else:
                    student.first_name = first
                    student.last_name = last
                    student.student_major = student_major

                existing = Enrollment.query.filter_by(
                    student_id=student.id, course_id=course_id, semester_id=sem_id
                ).first()
                if not existing:
                    db.session.add(Enrollment(
                        student_id=student.id, course_id=course_id, semester_id=sem_id
                    ))
                    added += 1
                else:
                    skipped += 1

            except Exception as e:
                errors.append(f'Row {i}: {e}')

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f'Import failed while saving records: {exc}', 'danger')
            results = {'added': added, 'skipped': skipped, 'errors': errors + [f'Commit error: {exc}'], 'semester': sem.label}
        else:
            results = {'added': added, 'skipped': skipped, 'errors': errors, 'semester': sem.label}

    return render_template('admin/import.html', semesters=semesters_list, results=results)


# ---------------------------------------------------------------------------  
# Student management
# ---------------------------------------------------------------------------
@admin_bp.route('/students')
@login_required
def students():
    _require_admin()
    all_students = Student.query.order_by(Student.last_name, Student.first_name).all()
    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    _require_admin()
    student = Student.query.get_or_404(student_id)
    
    # Get enrollments with semester info
    enrollments = db.session.query(Enrollment, Semester).join(Semester).filter(
        Enrollment.student_id == student_id
    ).order_by(Semester.year.desc(), Semester.term).all()
    
    # Get assessment details with batch and faculty info
    assessments = db.session.query(AssessmentDetail, AssessmentBatch, Faculty, Course, Semester).join(
        AssessmentBatch, AssessmentDetail.batch_id == AssessmentBatch.id
    ).join(
        Faculty, AssessmentBatch.faculty_id == Faculty.id
    ).join(
        Course, AssessmentBatch.course_id == Course.id
    ).join(
        Semester, AssessmentBatch.semester_id == Semester.id
    ).filter(
        AssessmentDetail.student_id == student_id
    ).order_by(AssessmentBatch.created_at.desc()).all()
    
    if not assessments:
        return render_template('admin/student_no_assessments.html', student=student)
    
    return render_template('admin/student_detail.html', 
                         student=student, 
                         enrollments=enrollments, 
                         assessments=assessments)


@admin_bp.route('/faculty/<int:faculty_id>')
@login_required
def faculty_detail(faculty_id):
    _require_admin()
    faculty = Faculty.query.get_or_404(faculty_id)
    
    # Get all batches by this faculty
    batches = AssessmentBatch.query.filter_by(faculty_id=faculty_id).order_by(
        AssessmentBatch.created_at.desc()
    ).all()
    
    # Get assessment details with student and batch info
    assessments = db.session.query(AssessmentDetail, AssessmentBatch, Student, Course, Semester).join(
        AssessmentBatch, AssessmentDetail.batch_id == AssessmentBatch.id
    ).join(
        Student, AssessmentDetail.student_id == Student.id
    ).join(
        Course, AssessmentBatch.course_id == Course.id
    ).join(
        Semester, AssessmentBatch.semester_id == Semester.id
    ).filter(
        AssessmentBatch.faculty_id == faculty_id
    ).order_by(AssessmentBatch.created_at.desc(), Student.last_name, Student.first_name).all()
    
    return render_template('admin/faculty_detail.html', 
                         faculty=faculty, 
                         batches=batches, 
                         assessments=assessments)
