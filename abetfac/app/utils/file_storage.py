import os
from flask import current_app, send_file, abort
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx'}


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_artifact(file_obj, batch, student):
    """
    Save an uploaded file to the structured upload directory.
    Returns (relative_path, original_filename) or None if invalid.
    """
    if not file_obj or not file_obj.filename:
        return None
    if not _allowed(file_obj.filename):
        return None

    upload_root = current_app.config['UPLOAD_ROOT']
    sem_label = batch.semester.label.replace(' ', '_')
    course_safe = batch.course_id.replace(' ', '')
    folder = os.path.join(upload_root, sem_label, course_safe, f'batch_{batch.id}')
    os.makedirs(folder, exist_ok=True)

    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    base = secure_filename(f'{student.last_name}_{student.first_name}_{file_obj.filename}')
    dest = os.path.join(folder, base)

    # Avoid collisions
    counter = 2
    root, dot_ext = os.path.splitext(dest)
    while os.path.exists(dest):
        dest = f'{root}_v{counter}{dot_ext}'
        counter += 1

    file_obj.save(dest)

    # Store path relative to upload_root
    rel_path = os.path.relpath(dest, upload_root)
    return rel_path, file_obj.filename


def serve_artifact(rel_path, original_filename=None):
    """
    Serve an artifact file safely, guarding against path traversal.
    """
    upload_root = os.path.realpath(current_app.config['UPLOAD_ROOT'])
    abs_path = os.path.realpath(os.path.join(upload_root, rel_path))

    if not abs_path.startswith(upload_root + os.sep) and abs_path != upload_root:
        abort(403)

    if not os.path.isfile(abs_path):
        abort(404)

    return send_file(abs_path,
                     as_attachment=False,
                     download_name=original_filename or os.path.basename(abs_path))


def delete_artifact(rel_path):
    """Delete an artifact file. Silently ignores missing files."""
    upload_root = current_app.config['UPLOAD_ROOT']
    abs_path = os.path.realpath(os.path.join(upload_root, rel_path))
    real_root = os.path.realpath(upload_root)

    if not abs_path.startswith(real_root + os.sep):
        return  # Safety: never delete outside upload root

    try:
        os.remove(abs_path)
    except FileNotFoundError:
        pass
