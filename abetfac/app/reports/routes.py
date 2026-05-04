from flask import Blueprint, render_template, request, abort, send_file
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import func
from app import db
from app.models import (AssessmentBatch, AssessmentDetail, Course, Semester,
                        SLO, CourseSLO, RubricCriterion, Enrollment)
from app.utils.export import build_excel_export

reports_bp = Blueprint('reports', __name__)


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@reports_bp.route('/course/<course_id>')
@login_required
def course_report(course_id):
    course = Course.query.get_or_404(course_id)
    sem_filter = request.args.get('semester_id', type=int)
    semesters = Semester.query.order_by(Semester.year.desc(), Semester.term).all()

    query = AssessmentBatch.query.filter_by(course_id=course_id)
    if sem_filter:
        query = query.filter_by(semester_id=sem_filter)
    batches = query.order_by(AssessmentBatch.semester_id).all()

    # Aggregate scores per SLO per criterion
    criteria = RubricCriterion.query.order_by(RubricCriterion.display_order).all()
    SCORE_FIELDS = AssessmentDetail.SCORE_FIELDS

    agg = {}  # slo_code -> {field -> [scores]}
    for batch in batches:
        slo_code = batch.slo.code
        if slo_code not in agg:
            agg[slo_code] = {field: [] for field, _ in SCORE_FIELDS}
        for d in batch.details.all():
            for field, _ in SCORE_FIELDS:
                s = getattr(d, field)
                if s:
                    agg[slo_code][field].append(s)

    # Compute averages
    avg_agg = {}
    for slo_code, fields in agg.items():
        avg_agg[slo_code] = {}
        for field, scores in fields.items():
            avg_agg[slo_code][field] = round(sum(scores) / len(scores), 2) if scores else None

    return render_template('reports/course_summary.html',
                           course=course, batches=batches,
                           semesters=semesters, sem_filter=sem_filter,
                           criteria=criteria, avg_agg=avg_agg,
                           SCORE_FIELDS=SCORE_FIELDS)


@reports_bp.route('/program')
@login_required
def program_report():
    _require_admin()
    sem_filter = request.args.get('semester_id', type=int)
    semesters = Semester.query.order_by(Semester.year.desc(), Semester.term).all()

    query = AssessmentBatch.query
    if sem_filter:
        query = query.filter_by(semester_id=sem_filter)
    batches = query.order_by(AssessmentBatch.course_id).all()

    SCORE_FIELDS = AssessmentDetail.SCORE_FIELDS
    criteria = RubricCriterion.query.order_by(RubricCriterion.display_order).all()

    # Per-SLO aggregate across all courses
    slo_agg = {}
    for batch in batches:
        slo_code = batch.slo.code
        if slo_code not in slo_agg:
            slo_agg[slo_code] = {'counts': 0, 'scores': {field: [] for field, _ in SCORE_FIELDS}}
        for d in batch.details.all():
            slo_agg[slo_code]['counts'] += 1
            for field, _ in SCORE_FIELDS:
                s = getattr(d, field)
                if s:
                    slo_agg[slo_code]['scores'][field].append(s)

    # Averages
    slo_avgs = {}
    for slo_code, data in slo_agg.items():
        slo_avgs[slo_code] = {
            'count': data['counts'],
            'fields': {}
        }
        for field, scores in data['scores'].items():
            slo_avgs[slo_code]['fields'][field] = (
                round(sum(scores) / len(scores), 2) if scores else None
            )

    return render_template('reports/program_report.html',
                           batches=batches, semesters=semesters,
                           sem_filter=sem_filter, slo_avgs=slo_avgs,
                           criteria=criteria, SCORE_FIELDS=SCORE_FIELDS)


@reports_bp.route('/enrollment-dashboard')
@login_required
def enrollment_dashboard():
    _require_admin()
    sem_filter = request.args.get('semester_id', type=int)
    selected_course_id = request.args.get('course_id', type=str)

    semesters = Semester.query.order_by(Semester.year.asc(), Semester.term.asc()).all()
    courses = Course.query.order_by(Course.id).all()

    enrollment_query = Enrollment.query
    if sem_filter:
        enrollment_query = enrollment_query.filter_by(semester_id=sem_filter)

    total_enrollments = enrollment_query.count()
    unique_students = db.session.query(func.count(func.distinct(Enrollment.student_id)))
    if sem_filter:
        unique_students = unique_students.filter(Enrollment.semester_id == sem_filter)
    unique_students = unique_students.scalar() or 0

    semester_counts = db.session.query(
        Semester.label.label('label'),
        func.count(Enrollment.id).label('count')
    ).join(Enrollment).group_by(Semester.id)
    if sem_filter:
        semester_counts = semester_counts.filter(Enrollment.semester_id == sem_filter)
    semester_counts = semester_counts.order_by(Semester.year.desc(), Semester.term).all()

    course_counts = db.session.query(
        Course.id.label('id'),
        Course.name.label('name'),
        func.count(Enrollment.id).label('count')
    ).join(Enrollment).group_by(Course.id)
    if sem_filter:
        course_counts = course_counts.filter(Enrollment.semester_id == sem_filter)
    course_counts = course_counts.order_by(Course.id).all()

    trend_query = db.session.query(
        Course.id.label('course_id'),
        Course.name.label('course_name'),
        Semester.label.label('semester_label'),
        func.count(Enrollment.id).label('count')
    ).join(Enrollment, Course.id == Enrollment.course_id)
    if sem_filter:
        trend_query = trend_query.filter(Enrollment.semester_id == sem_filter)
    trend_query = trend_query.join(Semester, Semester.id == Enrollment.semester_id)
    trend_query = trend_query.group_by(Course.id, Semester.id).order_by(Course.id, Semester.year.asc(), Semester.term.asc()).all()

    trend_data = {course.id: [0] * len(semesters) for course in courses}
    for row in trend_query:
        if row.course_id in trend_data:
            try:
                index = [s.label for s in semesters].index(row.semester_label)
            except ValueError:
                continue
            trend_data[row.course_id][index] = row.count

    courses_with_enrollment = len(course_counts)
    selected_course = None

    if selected_course_id:
        selected_course = Course.query.get(selected_course_id)
    elif courses:
        selected_course = courses[0]

    chart_labels = [s.label for s in semesters]
    chart_values = trend_data.get(selected_course.id, []) if selected_course else []

    return render_template('reports/enrollment_report.html',
                           semesters=semesters,
                           courses=courses,
                           sem_filter=sem_filter,
                           selected_course=selected_course,
                           selected_course_id=(selected_course.id if selected_course else None),
                           total_enrollments=total_enrollments,
                           unique_students=unique_students,
                           courses_with_enrollment=courses_with_enrollment,
                           semester_counts=semester_counts,
                           course_counts=course_counts,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           trend_data=trend_data)


@reports_bp.route('/export')
@login_required
def export_all():
    _require_admin()
    sem_filter = request.args.get('semester_id', type=int)
    buf = build_excel_export(semester_id=sem_filter)

    ts = datetime.now(timezone.utc).strftime('%Y%m%d')
    filename = f'ABET_Assessment_Export_{ts}.xlsx'
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)
