import os

SECRET_KEY = 'change-this-before-going-live'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "abet.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Absolute path where uploaded artifacts are stored.
# Change this to a shared drive path if needed (e.g. r'D:\ABET_Artifacts').
UPLOAD_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'uploads')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx'}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
