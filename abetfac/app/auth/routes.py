from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Faculty, LoginHistory

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('faculty.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = Faculty.query.filter(func.lower(Faculty.username) == username).first()
        if user and user.check_password(password):
            now = datetime.now(timezone.utc)
            user.last_login = now
            db.session.add(LoginHistory(faculty_id=user.id, logged_in_at=now))
            db.session.commit()
            login_user(user, remember=remember)
            if user.force_password_reset:
                flash('Please change your password before continuing.', 'warning')
                return redirect(url_for('auth.change_password'))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('faculty.dashboard'))
        flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from app import db
    error = None
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            error = 'Current password is incorrect.'
        elif len(new_pw) < 8:
            error = 'New password must be at least 8 characters.'
        elif new_pw != confirm_pw:
            error = 'Passwords do not match.'
        else:
            current_user.set_password(new_pw)
            current_user.force_password_reset = False
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('faculty.dashboard'))

    return render_template('auth/change_password.html', error=error)
