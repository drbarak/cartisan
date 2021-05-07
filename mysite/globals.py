import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'asdfjlkghdsf_drbarak'
    DEBUG = True
    UPLOAD_FOLDER ='/home/drbarak/mysite/csv'
    ALLOWED_EXTENSIONS = {'csv'}

class Globals:
    app = None
