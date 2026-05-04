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
    _seed_faculty()
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
        # id, name, credits, schedule_type, special_attributes, core_designations, programs
        ('CE 262', 'Civil & Construction Materials', 3, 'Laboratory; Lecture', 'Lab Included', None, [arche, cive, cone, enve]),
        ('CE 320', 'Intro to Environmental Eng', 3, 'Lecture', 'Recitation Included', None, [cive, enve]),
        ('CE 331', 'Intro to Structural Eng', 3, 'Lecture', None, None, [arche, cive, cone]),
        ('CE 340', 'Geotechnical Engineering', 4, 'Laboratory; Lecture', 'Lab Included', 'Computer Science; Writing', [arche, cive, cone, enve]),
        ('CE 350', 'Intro to Transportation Eng', 3, 'Lecture', None, None, [arche, cive]),
        ('CE 366', 'Intro to Construction Eng', 3, 'Lecture', None, None, [cive, cone]),
        ('CE 378', 'Water Resources Engineering', 3, 'Lecture', None, None, [cive, enve]),
        ('CE 401+', 'Capstone Design (Site Develop)', 4, 'Lecture/Laboratory Combined', None, 'Computer Science; Experiential Learning; Writing', [cive, cone, enve]),
        ('CE 403+', 'Capstone Design (Bldg Systems)', 4, 'Lecture/Laboratory Combined', None, 'Computer Science; Experiential Learning; Writing', [arche, cive, cone]),
        ('CE 420', 'Environmental Measurements', 3, 'Laboratory; Lecture', 'Spring Only; Lab Included', None, [cive, enve]),
        ('CE 422', 'Solid & Hazardous Waste Manag', 3, 'Lecture', 'Fall Only', None, [enve]),
        ('CE 424', 'Water & Wastewater Treatment', 3, 'Lecture', None, None, [cive, enve]),
        ('CE 425', 'Air Quality Engineering', 3, 'Lecture', '400/500-level Listing', None, [enve]),
        ('CE 433', 'Reinforced Concrete Structures I', 3, 'Lecture', 'Fall Only; Recitation Included', None, [arche, cive]),
        ('CE 434', 'Structural Steel Design I', 3, 'Lecture', 'Recitation Included', None, [arche, cive]),
        ('CE 451', 'Roadway Intersection Design', 3, 'Lecture', None, None, [cive]),
        ('CE 458', 'Traffic Engineering', 3, 'Lecture/Laboratory Combined', '400/500-level Listing', None, [cive]),
        ('CE 461', 'Horizontal Construction Methods', 3, 'Lecture', 'Fall Only; 400/500-level Listing', None, [cone]),
        ('CE 462', 'Vertical Construction Methods', 3, 'Lecture', 'Spring Only; 400/500-level Listing', None, [arche, cive, cone]),
        ('CE 463', 'Construction Cost Estimating', 3, 'Lecture', 'Spring Only; 400/500-level Listing', None, [cone]),
        ('CE 464', 'Safety Engineering', 3, 'Lecture', None, None, [cone]),
        ('CE 468', 'Construction Scheduling', 3, 'Lecture', 'Fall Only; 400/500-level Listing', None, [cive, cone]),
        ('CE 475', 'Hydrology', 3, 'Lecture', None, None, [cive, enve]),
    ]
    for row in courses:
        cid, name, credits, sched, special, core, progs = row
        course = Course.query.get(cid)
        if course:
            course.name = name
            course.credit_hours = credits
            course.schedule_type = sched
            course.special_attributes = special
            course.core_designations = core
            course.programs = progs
        else:
            course = Course(
                id=cid, name=name, credit_hours=credits,
                schedule_type=sched, special_attributes=special,
                core_designations=core
            )
            course.programs.extend(progs)
            db.session.add(course)


# ---------------------------------------------------------------------------
# Course-SLO mappings  (from SLO_Assessed_Per_Course / Assessment in Access DB)
# ---------------------------------------------------------------------------
def _seed_course_slos():
    db.session.flush()
    mappings = [
        ('CE 262', ['SO3', 'SO6']),
        ('CE 320', ['SO1']),
        ('CE 331', ['SO1']),
        ('CE 340', ['SO3', 'SO6']),
        ('CE 350', ['SO1', 'SO4']),
        ('CE 366', ['SO1', 'SO4']),
        ('CE 378', ['SO1']),
        ('CE 401+', ['SO2', 'SO3', 'SO4', 'SO5', 'SO7']),
        ('CE 403+', ['SO2', 'SO3', 'SO4', 'SO5', 'SO7']),
        ('CE 420', ['SO5', 'SO6']),
        ('CE 422', ['SO1']),
        ('CE 424', ['SO2', 'SO3', 'SO4', 'SO7']),
        ('CE 425', ['SO2', 'SO3', 'SO4']),
        ('CE 433', ['SO4']),
        ('CE 434', ['SO2', 'SO7']),
        ('CE 451', ['SO2']),
        ('CE 458', ['SO2']),
        ('CE 461', ['SO1']),
        ('CE 462', ['SO2', 'SO7']),
        ('CE 463', ['SO4', 'SO5']),
        ('CE 464', ['SO1', 'SO4']),
        ('CE 468', ['SO2']),
        ('CE 475', ['SO2', 'SO7']),
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


def _seed_faculty():
    users = [
        ('Sriram Aaleti', 's_aaleti', 'saaleti@eng.ua.edu'),
        ('Kofi Adanu', 'k_adanu', 'ekadanu@ua.edu'),
        ('Armen Amirkhanian', 'a_amirkhanian', 'armen.amirkhanian@eng.ua.edu'),
        ('Barry Battle', 'b_battle', 'bbattle@eng.ua.edu'),
        ('Robert Bertini', 'r_bertini', 'rbertini@ua.edu'),
        ('Matthew Blair', 'm_blair', 'mblair4@ua.edu'),
        ('Steven Burian', 's_burian', 'sburian@ua.edu'),
        ('Kaiwen Chen', 'k_chen', 'kaiwen.chen@ua.edu'),
        ('Xiaowei Chen', 'x_chen', 'xchen122@ua.edu'),
        ('Prabhakar Clement', 'p_clement', 'pclement@ua.edu'),
        ('Shane Crawford', 's_crawford', 'pscrawford@ua.edu'),
        ('Thang Dao', 't_dao', 'tdao@eng.ua.edu'),
        ('Rhiannon Davidson', 'r_davidson', 'rldavidson1@ua.edu'),
        ('Anisha Deria', 'a_deria', 'aderia@ua.edu'),
        ('Lisa Duan', 'l_duan', 'qduan@ua.edu'),
        ('Mark Elliott', 'm_elliott', 'melliott@eng.ua.edu'),
        ('Mostafa Firouzjaei', 'm_firouzjaei', 'mdfirouzjaei@ua.edu'),
        ('Shady Gomaa', 's_gomaa', 'sgomaa@ua.edu'),
        ('Alex Hainen', 'a_hainen', 'ahainen@ua.edu'),
        ('Daqian Jiang', 'd_jiang', 'djiang6@ua.edu'),
        ('Peishi Jiang', 'p_jiang', 'peishi.jiang@ua.edu'),
        ('Steven Jones', 's_jones', 'steven.jones@ua.edu'),
        ('Hannah Kessler', 'h_kessler', 'hkessler@ua.edu'),
        ('Mukesh Kumar', 'm_kumar', 'mkumar4@ua.edu'),
        ('Daan Liang', 'd_liang', 'dliang5@ua.edu'),
        ('Abhay Lidbe', 'a_lidbe', 'adlilbe@ua.edu'),
        ('Mesfin Mekonnen', 'm_mekonnen', 'mesfin.mekonnen@ua.edu'),
        ('Hamed Moftakhari', 'h_moftakhari', 'hmoftakhari@eng.ua.edu'),
        ('Hamid Moradkhani', 'h_moradkhani', 'hmoradkhani@ua.edu'),
        ('Mariah Parker', 'm_parker', 'mmparker6@ua.edu'),
        ('Satya Patra', 's_patra', 'satya.patra@ua.edu'),
        ('Praveena Penmetsa', 'p_penmetsa', 'ppenmetsa@ua.edu'),
        ('Mizan Rahman', 'm_rahman', 'mizan.rahman@ua.edu'),
        ('Christopher Schemel', 'c_schemel', 'cschemel@ua.edu'),
        ('Lusiana Scott', 'l_scott', 'lscott31@ua.edu'),
        ('Lea Skelton', 'l_skelton', 'ehskelton@ua.edu'),
        ('Leigh Terry', 'l_terry', 'leigh.terry@ua.edu'),
        ('Glenn Tootle', 'g_tootle', 'gatootle@eng.ua.edu'),
        ('Jialai Wang', 'j_wang', 'jwang@eng.ua.edu'),
    ]

    for display_name, username, email in users:
        username = username.lower()
        if not Faculty.query.filter_by(username=username).first():
            user = Faculty(
                username=username,
                display_name=display_name,
                email=email,
                is_admin=False,
                force_password_reset=True,
            )
            user.set_password('changeme123')
            db.session.add(user)
