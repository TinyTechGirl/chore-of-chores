# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use an environment variable for production (e.g., on Heroku, DATABASE_URL is set automatically)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
