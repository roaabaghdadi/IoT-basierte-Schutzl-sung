import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DB_USER = os.environ.get('DB_USER')
    DB_PASS = os.environ.get('DB_PASS')
    DB_HOST = os.environ.get('DB_HOST')
    DB_NAME = os.environ.get('DB_NAME')

    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TEMP_THRESHOLD = 50.0
    HUMIDITY_THRESHOLD = 80
    GAS_THRESHOLD = 400
    CO_THRESHOLD = 100

# Gmail configuration
    GMAIL_EMAIL = 'roaabaghdadi9418@gmail.com'
    GMAIL_APP_PASSWORD = 'rlko ehqa poea xlkl'
