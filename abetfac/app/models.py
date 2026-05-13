from datetime import datetime, timezone
from flask_login import UserMixin
import bcrypt
from . import db, login_manager


class Faculty(UserMixin, db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    force_password_reset = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    batches = db.relationship('AssessmentBatch', back_populates='faculty',
                              cascade='all, delete-orphan', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'), self.password_hash.encode('utf-8')
        )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Faculty, int(user_id))


class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)

    courses = db.relationship('Course', secondary='course_programs', back_populates='programs', lazy='dynamic')


class SLO(db.Model):
    __tablename__ = 'slos'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    summary = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)

    peos = db.relationship('PEO', back_populates='slo', lazy='dynamic')
    course_slos = db.relationship('CourseSLO', back_populates='slo', lazy='dynamic')
    batches = db.relationship('AssessmentBatch', back_populates='slo', lazy='dynamic')


class PEO(db.Model):
    __tablename__ = 'peos'
    id = db.Column(db.Integer, primary_key=True)
    slo_id = db.Column(db.Integer, db.ForeignKey('slos.id'), nullable=False)
    brief_desc = db.Column(db.String(255))
    full_desc = db.Column(db.Text)

    slo = db.relationship('SLO', back_populates='peos')


course_programs = db.Table('course_programs',
    db.Column('course_id', db.String(20), db.ForeignKey('courses.id'), primary_key=True),
    db.Column('program_id', db.Integer, db.ForeignKey('programs.id'), primary_key=True)
)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    credit_hours = db.Column(db.Integer)
    schedule_type = db.Column(db.String(120))
    special_attributes = db.Column(db.String(255))
    core_designations = db.Column(db.String(255))

    programs = db.relationship('Program', secondary=course_programs, back_populates='courses')
    course_slos = db.relationship('CourseSLO', back_populates='course', lazy='dynamic')
    enrollments = db.relationship('Enrollment', back_populates='course', lazy='dynamic')
    batches = db.relationship('AssessmentBatch', back_populates='course', lazy='dynamic')


class CourseSLO(db.Model):
    __tablename__ = 'course_slos'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.id'), nullable=False)
    slo_id = db.Column(db.Integer, db.ForeignKey('slos.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('course_id', 'slo_id'),)

    course = db.relationship('Course', back_populates='course_slos')
    slo = db.relationship('SLO', back_populates='course_slos')


class Semester(db.Model):
    __tablename__ = 'semesters'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(40), unique=True, nullable=False)
    year = db.Column(db.Integer)
    term = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    enrollments = db.relationship('Enrollment', back_populates='semester', lazy='dynamic')
    batches = db.relationship('AssessmentBatch', back_populates='semester', lazy='dynamic')


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    elearn_id = db.Column(db.String(30), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    student_major = db.Column(db.String(50), nullable=False)

    enrollments = db.relationship('Enrollment', back_populates='student', lazy='dynamic')
    details = db.relationship('AssessmentDetail', back_populates='student', lazy='dynamic')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', 'semester_id'),)

    student = db.relationship('Student', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')
    semester = db.relationship('Semester', back_populates='enrollments')


class RubricCriterion(db.Model):
    __tablename__ = 'rubric_criteria'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)
    exemplary_desc = db.Column(db.Text)
    adequate_desc = db.Column(db.Text)
    minimal_desc = db.Column(db.Text)
    unsatisfactory_desc = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)


class AssessmentBatch(db.Model):
    __tablename__ = 'assessment_batches'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    slo_id = db.Column(db.Integer, db.ForeignKey('slos.id'), nullable=False)
    outcome_assessed = db.Column(db.String(255))
    action_taken = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('course_id', 'faculty_id', 'semester_id', 'slo_id'),)

    course = db.relationship('Course', back_populates='batches')
    faculty = db.relationship('Faculty', back_populates='batches')
    semester = db.relationship('Semester', back_populates='batches')
    slo = db.relationship('SLO', back_populates='batches')
    details = db.relationship('AssessmentDetail', back_populates='batch',
                              cascade='all, delete-orphan', lazy='dynamic')

    @property
    def assessed_count(self):
        return self.details.count()

    @property
    def enrolled_count(self):
        return Enrollment.query.filter_by(
            course_id=self.course_id, semester_id=self.semester_id
        ).count()


class AssessmentDetail(db.Model):
    __tablename__ = 'assessment_details'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('assessment_batches.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    artifact_path = db.Column(db.String(500), unique=True)
    artifact_filename = db.Column(db.String(255))
    earned_grade = db.Column(db.String(10))
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    score_organization = db.Column(db.Integer)
    score_formatting = db.Column(db.Integer)
    score_content = db.Column(db.Integer)
    score_references = db.Column(db.Integer)
    score_graphical_comm = db.Column(db.Integer)
    score_safe_lab = db.Column(db.Integer)
    score_data_analysis = db.Column(db.Integer)
    score_eng_conclusions = db.Column(db.Integer)

    batch = db.relationship('AssessmentBatch', back_populates='details')
    student = db.relationship('Student', back_populates='details')

    # Map form field names to column names for easy iteration
    SCORE_FIELDS = [
        ('score_organization', 'Organization'),
        ('score_formatting', 'Formatting'),
        ('score_content', 'Content'),
        ('score_references', 'References'),
        ('score_graphical_comm', 'Graphical Communication'),
        ('score_safe_lab', 'Conduct Safe Lab Experiments'),
        ('score_data_analysis', 'Analyze & Interpret Data'),
        ('score_eng_conclusions', 'Draw Engineering Conclusions'),
    ]

    def scores_dict(self):
        return {label: getattr(self, field) for field, label in self.SCORE_FIELDS}
