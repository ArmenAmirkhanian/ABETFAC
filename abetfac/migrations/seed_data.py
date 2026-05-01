"""
Run once after create_app() initializes the DB to populate reference data
from the original Access database.

Usage:
    cd abetfac
    python -c "from migrations.seed_data import seed; from app import create_app; app=create_app(); app.app_context().push(); seed()"
"""

from app import db
from app.models import Faculty, Program, SLO, PEO, Course, CourseSLO, RubricCriterion, Semester


def seed():
    _seed_programs()
    _seed_slos()
    _seed_peos()
    _seed_courses()
    _seed_course_slos()
    _seed_rubric_criteria()
    _seed_semesters()
    _seed_admin()
    db.session.commit()
    print("Seed data inserted successfully.")


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------
def _seed_programs():
    programs = [
        ('ArchE', 'Architecture Engineering'),
        ('CivE', 'Civil Engineering'),
        ('ConE', 'Construction Engineering'),
        ('EnvE', 'Environmental Engineering'),
    ]
    for code, name in programs:
        if not Program.query.filter_by(code=code).first():
            db.session.add(Program(code=code, full_name=name))


# ---------------------------------------------------------------------------
# Student Learning Outcomes
# ---------------------------------------------------------------------------
def _seed_slos():
    slos = [
        ('SO1', 'Complex Problem Solving',
         'Identify, formulate, and solve complex engineering problems by applying '
         'principles of engineering, science, and mathematics.'),
        ('SO2', 'Design',
         'Apply engineering design to produce solutions that meet specified needs with '
         'consideration of public health, safety, welfare, and global, cultural, social, '
         'environmental, and economic factors.'),
        ('SO3', 'Communication',
         'Communicate effectively with a range of audiences.'),
        ('SO4', 'Ethics',
         'Recognize ethical and professional responsibilities in engineering situations '
         'and make informed judgments.'),
        ('SO5', 'Teamwork',
         'Function effectively on a team whose members together provide leadership, '
         'create a collaborative and inclusive environment, establish goals, plan tasks, '
         'and meet objectives.'),
        ('SO6', 'Experiments',
         'Develop and conduct appropriate experimentation, analyze and interpret data, '
         'and use engineering judgment to draw conclusions.'),
        ('SO7', 'Learning',
         'Acquire and apply new knowledge as needed, using appropriate learning strategies.'),
    ]
    for code, summary, desc in slos:
        if not SLO.query.filter_by(code=code).first():
            db.session.add(SLO(code=code, summary=summary, description=desc))


# ---------------------------------------------------------------------------
# Program Educational Outcomes
# ---------------------------------------------------------------------------
def _seed_peos():
    db.session.flush()
    peo_data = [
        ('SO1', 'Knowledge Application and Judgment',
         'Graduates will apply their technical knowledge and engineering judgment to '
         'solve real-world problems in their disciplines.'),
        ('SO3', 'Communication and Collaboration',
         'Graduates will communicate and collaborate effectively with diverse stakeholders.'),
        ('SO4', 'Ethics and Professional Responsibility',
         'Graduates will practice their profession with integrity and ethical responsibility.'),
        ('SO7', 'Continuous Learning and Professional Development',
         'Graduates will engage in life-long learning to advance professionally and '
         'adapt to new technologies and challenges.'),
    ]
    for slo_code, brief, full in peo_data:
        slo = SLO.query.filter_by(code=slo_code).first()
        if slo and not PEO.query.filter_by(slo_id=slo.id, brief_desc=brief).first():
            db.session.add(PEO(slo_id=slo.id, brief_desc=brief, full_desc=full))


# ---------------------------------------------------------------------------
# Courses  (from General_Course_Info in the Access DB)
# ---------------------------------------------------------------------------
def _seed_courses():
    cive = Program.query.filter_by(code='CivE').first()
    cone = Program.query.filter_by(code='ConE').first()
    enve = Program.query.filter_by(code='EnvE').first()
    arche = Program.query.filter_by(code='ArchE').first()

    courses = [
        # id, name, credits, schedule_type, special_attributes, core_designations, program
        ('CE 101', 'Introduction to Civil Engineering', 1, 'Lecture', None, None, cive),
        ('CE 201', 'Engineering Statics', 3, 'Lecture', None, None, cive),
        ('CE 211', 'Engineering Dynamics', 3, 'Lecture', None, None, cive),
        ('CE 215', 'Mechanics of Materials', 3, 'Lecture', None, None, cive),
        ('CE 262', 'Civil & Construction Materials', 3, 'Laboratory, Lecture', 'Lab Included', 'Writing', cive),
        ('CE 301', 'Structural Analysis', 3, 'Lecture', None, None, cive),
        ('CE 310', 'Fluid Mechanics', 3, 'Lecture', None, None, cive),
        ('CE 315', 'Soil Mechanics', 3, 'Laboratory, Lecture', 'Lab Included', None, cive),
        ('CE 320', 'Transportation Engineering', 3, 'Lecture', None, None, cive),
        ('CE 325', 'Environmental Engineering', 3, 'Lecture', None, None, enve),
        ('CE 330', 'Structural Steel Design', 3, 'Lecture', None, None, cive),
        ('CE 335', 'Reinforced Concrete Design', 3, 'Lecture', None, None, cive),
        ('CE 340', 'Hydraulics & Hydrology', 3, 'Laboratory, Lecture', 'Lab Included', None, cive),
        ('CE 350', 'Construction Planning & Scheduling', 3, 'Lecture', None, 'Writing', cone),
        ('CE 355', 'Construction Cost Estimating', 3, 'Lecture', None, None, cone),
        ('CE 360', 'Geotechnical Engineering', 3, 'Lecture', None, None, cive),
        ('CE 401', 'Senior Design I', 2, 'Lecture', None, None, cive),
        ('CE 402', 'Senior Design II', 3, 'Lecture', None, 'Writing', cive),
        ('CE 410', 'Water Resources Engineering', 3, 'Lecture', None, None, enve),
        ('CE 420', 'Foundation Engineering', 3, 'Lecture', None, None, cive),
        ('CE 430', 'Environmental Site Assessment', 3, 'Lecture', None, None, enve),
        ('CE 440', 'Construction Management', 3, 'Lecture', None, None, cone),
        ('CE 450', 'Bridge Design', 3, 'Lecture', None, None, cive),
    ]
    for row in courses:
        cid, name, credits, sched, special, core, prog = row
        if not Course.query.get(cid):
            db.session.add(Course(
                id=cid, name=name, credit_hours=credits,
                schedule_type=sched, special_attributes=special,
                core_designations=core,
                program_id=prog.id if prog else None
            ))


# ---------------------------------------------------------------------------
# Course-SLO mappings  (from SLO_Assessed_Per_Course / Assessment in Access DB)
# ---------------------------------------------------------------------------
def _seed_course_slos():
    db.session.flush()
    mappings = [
        ('CE 262', ['SO3', 'SO6']),
        ('CE 301', ['SO1', 'SO2']),
        ('CE 310', ['SO1', 'SO6']),
        ('CE 315', ['SO1', 'SO6']),
        ('CE 320', ['SO1', 'SO3']),
        ('CE 325', ['SO1', 'SO2', 'SO6']),
        ('CE 330', ['SO1', 'SO2']),
        ('CE 335', ['SO1', 'SO2']),
        ('CE 340', ['SO1', 'SO6']),
        ('CE 350', ['SO3', 'SO5']),
        ('CE 355', ['SO1', 'SO5']),
        ('CE 360', ['SO1', 'SO6']),
        ('CE 401', ['SO2', 'SO5']),
        ('CE 402', ['SO2', 'SO3', 'SO4']),
        ('CE 410', ['SO1', 'SO2', 'SO6']),
        ('CE 420', ['SO1', 'SO2']),
        ('CE 430', ['SO1', 'SO6']),
        ('CE 440', ['SO3', 'SO4', 'SO5']),
        ('CE 450', ['SO1', 'SO2']),
    ]
    for course_id, slo_codes in mappings:
        for code in slo_codes:
            slo = SLO.query.filter_by(code=code).first()
            if slo and not CourseSLO.query.filter_by(course_id=course_id, slo_id=slo.id).first():
                db.session.add(CourseSLO(course_id=course_id, slo_id=slo.id))


# ---------------------------------------------------------------------------
# Rubric Criteria  (from Rubric_Guidance in Access DB)
# ---------------------------------------------------------------------------
def _seed_rubric_criteria():
    criteria = [
        (1, 'score_organization', 'Organization',
         'Presents information in a logical, interesting sequence which audience can follow.',
         'Presents information in a logical sequence which audience can follow with some effort.',
         'Audience has difficulty following presentation because student jumps around.',
         'Audience cannot understand presentation because there is no sequence of information.'),
        (2, 'score_formatting', 'Formatting',
         'Uses a consistent format throughout the document with excellent visual presentation.',
         'Uses a mostly consistent format with minor inconsistencies.',
         'Format is inconsistent in several places, reducing readability.',
         'Format is absent or so inconsistent that it seriously impairs readability.'),
        (3, 'score_content', 'Content',
         'Demonstrates full knowledge with explanations and elaboration.',
         'Is at ease with expected answers to most questions, without elaboration.',
         'Is uncomfortable with information and is able to answer only rudimentary questions.',
         'Does not have grasp of information; student cannot answer questions about subject.'),
        (4, 'score_references', 'References',
         'All references are properly cited and formatted consistently. Sources are authoritative.',
         'Most references are cited. Minor formatting inconsistencies. Sources are adequate.',
         'Some references are missing or improperly cited. Some sources are questionable.',
         'References are absent or so improperly cited that sources cannot be verified.'),
        (5, 'score_graphical_comm', 'Graphical Communication',
         'Graphics and figures are clear, well-labeled, and effectively convey key information.',
         'Graphics are mostly clear with minor labeling or clarity issues.',
         'Graphics are present but are difficult to interpret or poorly labeled.',
         'No graphics used, or graphics present are confusing and detract from the work.'),
        (6, 'score_safe_lab', 'Conduct Safe Lab Experiments',
         'Demonstrates full understanding and application of safety protocols at all times.',
         'Generally follows safety protocols with minor lapses.',
         'Safety protocols are followed inconsistently; requires reminders.',
         'Does not follow safety protocols; poses a risk to self or others.'),
        (7, 'score_data_analysis', 'Analyze & Interpret Data w/ Uncertainty',
         'Correctly analyzes data, quantifies uncertainty, and draws statistically sound conclusions.',
         'Analyzes data with minor errors; addresses uncertainty at a basic level.',
         'Analysis contains significant errors or ignores uncertainty.',
         'Data analysis is absent or fundamentally flawed.'),
        (8, 'score_eng_conclusions', 'Draw Engineering Conclusions',
         'Conclusions are clearly supported by data and engineering principles; limitations noted.',
         'Conclusions follow from data with minor unsupported claims.',
         'Conclusions are partially supported; some are unsupported or incorrect.',
         'Conclusions are absent, unsupported by data, or fundamentally incorrect.'),
    ]
    for order, code, label, ex, ad, mn, un in criteria:
        if not RubricCriterion.query.filter_by(code=code).first():
            db.session.add(RubricCriterion(
                code=code, label=label, display_order=order,
                exemplary_desc=ex, adequate_desc=ad,
                minimal_desc=mn, unsatisfactory_desc=un
            ))


# ---------------------------------------------------------------------------
# Semesters
# ---------------------------------------------------------------------------
def _seed_semesters():
    semesters = [
        (2024, 'Spring'), (2024, 'Fall'),
        (2025, 'Spring'), (2025, 'Fall'),
        (2026, 'Spring'), (2026, 'Fall'),
        (2027, 'Spring'), (2027, 'Fall'),
        (2028, 'Spring'), (2028, 'Fall'),
    ]
    for year, term in semesters:
        label = f'{year} {term}'
        if not Semester.query.filter_by(label=label).first():
            is_active = (year == 2026 and term == 'Spring')
            db.session.add(Semester(label=label, year=year, term=term, is_active=is_active))


# ---------------------------------------------------------------------------
# Default admin account
# ---------------------------------------------------------------------------
def _seed_admin():
    if not Faculty.query.filter_by(username='admin').first():
        admin = Faculty(
            username='admin',
            display_name='Administrator',
            email='admin@example.com',
            is_admin=True,
            force_password_reset=True,
        )
        admin.set_password('changeme')
        db.session.add(admin)
        print("Default admin created — username: admin, password: changeme")
        print("IMPORTANT: Change this password immediately after first login.")
