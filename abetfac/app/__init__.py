import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True

    os.makedirs(app.config['UPLOAD_ROOT'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth.routes import auth_bp
    from .faculty.routes import faculty_bp
    from .admin.routes import admin_bp
    from .reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    with app.app_context():
        db.create_all()

    return app
