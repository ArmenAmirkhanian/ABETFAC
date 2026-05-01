from flask import Blueprint, render_template, request, abort, send_file
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models import (AssessmentBatch, AssessmentDetail, Course, Semester,
                        SLO, CourseSLO, RubricCriterion)
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
