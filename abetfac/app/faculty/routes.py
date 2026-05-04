import os
import csv
import io
from datetime import datetime, timezone
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, send_file, jsonify, Response, current_app)
from flask_login import login_required, current_user
from app import db
from app.models import (AssessmentBatch, AssessmentDetail, Course, Semester,
                        SLO, CourseSLO, Enrollment, Student, RubricCriterion,
                        Faculty)
from app.utils.file_storage import save_artifact, serve_artifact, delete_artifact

faculty_bp = Blueprint('faculty', __name__)

ASSESSMENT_COURSE_IDS = [
    'CE 262', 'CE 320', 'CE 331', 'CE 340', 'CE 350', 'CE 366', 'CE 378',
    'CE 401+', 'CE 403+', 'CE 420', 'CE 422', 'CE 424', 'CE 425', 'CE 433',
    'CE 434', 'CE 451', 'CE 458', 'CE 461', 'CE 462', 'CE 463', 'CE 468',
    'CE 475',
]

SCORE_FIELDS = AssessmentDetail.SCORE_FIELDS


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@faculty_bp.route('/')
@faculty_bp.route('/dashboard')
@login_required
def dashboard():
    active_sem = Semester.query.filter_by(is_active=True).first()
    if not active_sem:
        flash('No active semester is set. Ask an administrator to activate a semester.', 'warning')

    # Find courses this faculty has batches in, or all courses if admin
    if current_user.is_admin:
        batches = (AssessmentBatch.query
                   .filter_by(semester_id=active_sem.id if active_sem else None)
                   .order_by(AssessmentBatch.course_id)
                   .all()) if active_sem else []
        # Group by course
        course_batches = {}
        for b in batches:
            course_batches.setdefault(b.course_id, []).append(b)
        courses_with_batches = [(Course.query.get(cid), bs)
                                for cid, bs in course_batches.items()]
        all_courses = (Course.query
                       .filter(Course.id.in_(ASSESSMENT_COURSE_IDS))
                       .order_by(Course.id)
                       .all())
    else:
        batches = (AssessmentBatch.query
                   .filter_by(faculty_id=current_user.id,
                               semester_id=active_sem.id if active_sem else None)
                   .order_by(AssessmentBatch.course_id)
                   .all()) if active_sem else []
        course_batches = {}
        for b in batches:
            course_batches.setdefault(b.course_id, []).append(b)
        courses_with_batches = [(Course.query.get(cid), bs)
                                for cid, bs in course_batches.items()]
        all_courses = None

    semesters = Semester.query.order_by(Semester.year.desc(), Semester.term).all()
    return render_template('faculty/dashboard.html',
                           active_sem=active_sem,
                           courses_with_batches=courses_with_batches,
                           all_courses=all_courses,
                           semesters=semesters)


# ---------------------------------------------------------------------------
# HTMX fragments
# ---------------------------------------------------------------------------
@faculty_bp.route('/htmx/slos/<course_id>')
@login_required
def htmx_slos(course_id):
    course_slos = (CourseSLO.query
                   .filter_by(course_id=course_id)
                   .join(SLO)
                   .order_by(SLO.code)
                   .all())
    return render_template('faculty/_slo_options.html', course_slos=course_slos)


@faculty_bp.route('/htmx/students/<course_id>/<int:sem_id>')
@login_required
def htmx_students(course_id, sem_id):
    enrollments = (Enrollment.query
                   .filter_by(course_id=course_id, semester_id=sem_id)
                   .join(Student)
                   .order_by(Student.last_name, Student.first_name)
                   .all())
    return render_template('faculty/_student_options.html', enrollments=enrollments)


# ---------------------------------------------------------------------------
# Assessment Batches
# ---------------------------------------------------------------------------
@faculty_bp.route('/batches/new', methods=['GET', 'POST'])
@login_required
def batch_new():
    semesters = Semester.query.order_by(Semester.year.desc(), Semester.term).all()
    courses = (Course.query
               .filter(Course.id.in_(ASSESSMENT_COURSE_IDS))
               .order_by(Course.id)
               .all())
    active_sem = Semester.query.filter_by(is_active=True).first()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        semester_id = request.form.get('semester_id', type=int)
        slo_id = request.form.get('slo_id', type=int)
        outcome_assessed = request.form.get('outcome_assessed', '').strip()
        action_taken = request.form.get('action_taken', '').strip()

        if not all([course_id, semester_id, slo_id]):
            flash('Course, semester, and outcome are required.', 'danger')
        else:
            existing = AssessmentBatch.query.filter_by(
                course_id=course_id, faculty_id=current_user.id,
                semester_id=semester_id, slo_id=slo_id
            ).first()
            if existing:
                flash('An assessment batch for this course, semester, and outcome already exists.', 'warning')
                return redirect(url_for('faculty.batch_detail', batch_id=existing.id))

            batch = AssessmentBatch(
                course_id=course_id,
                faculty_id=current_user.id,
                semester_id=semester_id,
                slo_id=slo_id,
                outcome_assessed=outcome_assessed,
                action_taken=action_taken,
            )
            db.session.add(batch)
            db.session.commit()
            flash(f'Assessment batch created for {course_id}.', 'success')
            return redirect(url_for('faculty.batch_detail', batch_id=batch.id))

    selected_course = request.args.get('course_id', '')
    selected_sem = int(request.args.get('semester_id', active_sem.id if active_sem else 0))
    course_slos = []
    if selected_course:
        course_slos = (CourseSLO.query.filter_by(course_id=selected_course)
                       .join(SLO).order_by(SLO.code).all())

    return render_template('faculty/batch_new.html',
                           semesters=semesters, courses=courses,
                           active_sem=active_sem, selected_course=selected_course,
                           selected_sem=selected_sem, course_slos=course_slos)


@faculty_bp.route('/batches/<int:batch_id>')
@login_required
def batch_detail(batch_id):
    batch = _get_batch_or_403(batch_id)
    criteria = RubricCriterion.query.order_by(RubricCriterion.display_order).all()

    # All enrolled students for this course/semester
    enrollments = (Enrollment.query
                   .filter_by(course_id=batch.course_id, semester_id=batch.semester_id)
                   .join(Student)
                   .order_by(Student.last_name, Student.first_name)
                   .all())

    # Map student_id -> detail record for quick lookup
    assessed = {d.student_id: d for d in batch.details.all()}

    return render_template('faculty/batch_detail.html',
                           batch=batch, enrollments=enrollments,
                           assessed=assessed, criteria=criteria)


@faculty_bp.route('/batches/<int:batch_id>/edit', methods=['GET', 'POST'])
@login_required
def batch_edit(batch_id):
    batch = _get_batch_or_403(batch_id)
    slos = (CourseSLO.query.filter_by(course_id=batch.course_id)
            .join(SLO).order_by(SLO.code).all())

    if request.method == 'POST':
        batch.outcome_assessed = request.form.get('outcome_assessed', '').strip()
        batch.action_taken = request.form.get('action_taken', '').strip()
        new_slo_id = request.form.get('slo_id', type=int)
        if new_slo_id:
            batch.slo_id = new_slo_id
        db.session.commit()
        flash('Batch updated.', 'success')
        return redirect(url_for('faculty.batch_detail', batch_id=batch.id))

    return render_template('faculty/batch_edit.html', batch=batch, slos=slos)


@faculty_bp.route('/batches/<int:batch_id>/delete', methods=['POST'])
@login_required
def batch_delete(batch_id):
    batch = _get_batch_or_403(batch_id)
    # Delete artifact files
    for detail in batch.details.all():
        if detail.artifact_path:
            delete_artifact(detail.artifact_path)
    db.session.delete(batch)
    db.session.commit()
    flash('Assessment batch deleted.', 'info')
    return redirect(url_for('faculty.dashboard'))


# ---------------------------------------------------------------------------
# Assessment Details (rubric scoring)
# ---------------------------------------------------------------------------
@faculty_bp.route('/batches/<int:batch_id>/assess/new', methods=['GET', 'POST'])
@login_required
def assess_new(batch_id):
    batch = _get_batch_or_403(batch_id)
    criteria = RubricCriterion.query.order_by(RubricCriterion.display_order).all()

    # Already-assessed student IDs for this batch
    assessed_ids = {d.student_id for d in batch.details.all()}
    enrollments = (Enrollment.query
                   .filter_by(course_id=batch.course_id, semester_id=batch.semester_id)
                   .join(Student)
                   .order_by(Student.last_name, Student.first_name)
                   .all())

    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        earned_grade = request.form.get('earned_grade', '').strip()

        if not student_id:
            flash('Please select a student.', 'danger')
        elif student_id in assessed_ids:
            # Redirect to edit instead
            existing = AssessmentDetail.query.filter_by(
                batch_id=batch_id, student_id=student_id).first()
            if existing:
                return redirect(url_for('faculty.assess_edit',
                                        batch_id=batch_id, detail_id=existing.id))

        scores = {}
        missing = []
        for field, label in SCORE_FIELDS:
            val = request.form.get(field, type=int)
            if not val or val not in (1, 2, 3, 4):
                missing.append(label)
            scores[field] = val

        artifact_file = request.files.get('artifact')

        if missing:
            flash(f'Missing or invalid scores for: {", ".join(missing)}', 'danger')
        else:
            artifact_path = None
            artifact_filename = None
            if artifact_file and artifact_file.filename:
                student = db.session.get(Student, student_id)
                result = save_artifact(artifact_file, batch, student)
                if result is None:
                    flash('Invalid file type or file too large. Allowed: PDF, DOC, DOCX, PPT, PPTX (max 25 MB).', 'danger')
                    return render_template('faculty/assess_form.html',
                                           batch=batch, criteria=criteria,
                                           enrollments=enrollments, assessed_ids=assessed_ids,
                                           detail=None, scores={})
                artifact_path, artifact_filename = result

            detail = AssessmentDetail(
                batch_id=batch_id,
                student_id=student_id,
                earned_grade=earned_grade,
                artifact_path=artifact_path,
                artifact_filename=artifact_filename,
            )
            for field, _ in SCORE_FIELDS:
                setattr(detail, field, scores[field])

            db.session.add(detail)
            db.session.commit()
            flash('Assessment saved.', 'success')

            # Check if more students remain
            total = len(enrollments)
            done = batch.details.count()
            if done < total:
                return redirect(url_for('faculty.assess_new', batch_id=batch_id))
            else:
                flash(f'All {total} students assessed!', 'success')
                return redirect(url_for('faculty.batch_detail', batch_id=batch_id))

    return render_template('faculty/assess_form.html',
                           batch=batch, criteria=criteria,
                           enrollments=enrollments, assessed_ids=assessed_ids,
                           detail=None, scores={})


@faculty_bp.route('/batches/<int:batch_id>/assess/<int:detail_id>/edit', methods=['GET', 'POST'])
@login_required
def assess_edit(batch_id, detail_id):
    batch = _get_batch_or_403(batch_id)
    detail = AssessmentDetail.query.filter_by(id=detail_id, batch_id=batch_id).first_or_404()
    criteria = RubricCriterion.query.order_by(RubricCriterion.display_order).all()
    enrollments = (Enrollment.query
                   .filter_by(course_id=batch.course_id, semester_id=batch.semester_id)
                   .join(Student).order_by(Student.last_name, Student.first_name).all())
    assessed_ids = {d.student_id for d in batch.details.all()}

    if request.method == 'POST':
        detail.earned_grade = request.form.get('earned_grade', '').strip()

        scores = {}
        missing = []
        for field, label in SCORE_FIELDS:
            val = request.form.get(field, type=int)
            if not val or val not in (1, 2, 3, 4):
                missing.append(label)
            scores[field] = val

        if missing:
            flash(f'Missing or invalid scores for: {", ".join(missing)}', 'danger')
        else:
            for field, _ in SCORE_FIELDS:
                setattr(detail, field, scores[field])

            artifact_file = request.files.get('artifact')
            if artifact_file and artifact_file.filename:
                student = db.session.get(Student, detail.student_id)
                result = save_artifact(artifact_file, batch, student)
                if result is None:
                    flash('Invalid file type. Allowed: PDF, DOC, DOCX, PPT, PPTX (max 25 MB).', 'danger')
                else:
                    if detail.artifact_path:
                        delete_artifact(detail.artifact_path)
                    detail.artifact_path, detail.artifact_filename = result

            db.session.commit()
            flash('Assessment updated.', 'success')
            return redirect(url_for('faculty.batch_detail', batch_id=batch_id))

    scores = {field: getattr(detail, field) for field, _ in SCORE_FIELDS}
    return render_template('faculty/assess_form.html',
                           batch=batch, criteria=criteria,
                           enrollments=enrollments, assessed_ids=assessed_ids,
                           detail=detail, scores=scores)


@faculty_bp.route('/batches/<int:batch_id>/assess/<int:detail_id>/delete', methods=['POST'])
@login_required
def assess_delete(batch_id, detail_id):
    batch = _get_batch_or_403(batch_id)
    detail = AssessmentDetail.query.filter_by(id=detail_id, batch_id=batch_id).first_or_404()
    if detail.artifact_path:
        delete_artifact(detail.artifact_path)
    db.session.delete(detail)
    db.session.commit()
    flash('Assessment record deleted.', 'info')
    return redirect(url_for('faculty.batch_detail', batch_id=batch_id))


@faculty_bp.route('/batches/<int:batch_id>/assess/draft', methods=['POST'])
@login_required
def assess_draft(batch_id):
    # Lightweight endpoint — just acknowledge; client handles the timing
    return ('', 204)


@faculty_bp.route('/batches/<int:batch_id>/assess/<int:detail_id>/artifact')
@login_required
def serve_artifact_file(batch_id, detail_id):
    _get_batch_or_403(batch_id)
    detail = AssessmentDetail.query.filter_by(id=detail_id, batch_id=batch_id).first_or_404()
    if not detail.artifact_path:
        abort(404)
    return serve_artifact(detail.artifact_path, detail.artifact_filename)


# ---------------------------------------------------------------------------
# History & Export
# ---------------------------------------------------------------------------
@faculty_bp.route('/history')
@login_required
def history():
    if current_user.is_admin:
        batches = (AssessmentBatch.query
                   .order_by(AssessmentBatch.created_at.desc())
                   .all())
    else:
        batches = (AssessmentBatch.query
                   .filter_by(faculty_id=current_user.id)
                   .order_by(AssessmentBatch.created_at.desc())
                   .all())

    semesters = Semester.query.order_by(Semester.year.desc(), Semester.term).all()
    sem_filter = request.args.get('semester_id', type=int)
    if sem_filter:
        batches = [b for b in batches if b.semester_id == sem_filter]

    return render_template('faculty/history.html', batches=batches, semesters=semesters,
                           sem_filter=sem_filter)


@faculty_bp.route('/history/export/<int:batch_id>')
@login_required
def export_batch_csv(batch_id):
    batch = _get_batch_or_403(batch_id)
    output = io.StringIO()
    writer = csv.writer(output)

    headers = ['Student Last', 'Student First', 'ELEARN ID', 'Earned Grade',
               'Artifact'] + [label for _, label in SCORE_FIELDS]
    writer.writerow(headers)

    for d in batch.details.order_by(AssessmentDetail.id).all():
        row = [
            d.student.last_name, d.student.first_name, d.student.elearn_id,
            d.earned_grade or '', d.artifact_filename or ''
        ] + [getattr(d, field) for field, _ in SCORE_FIELDS]
        writer.writerow(row)

    output.seek(0)
    sem_label = batch.semester.label.replace(' ', '_')
    filename = f'ABET_{batch.course_id.replace(" ", "")}_{sem_label}_SLO{batch.slo.code}.csv'
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_batch_or_403(batch_id):
    batch = AssessmentBatch.query.get_or_404(batch_id)
    if not current_user.is_admin and batch.faculty_id != current_user.id:
        abort(403)
    return batch
