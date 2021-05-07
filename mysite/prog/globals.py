import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'asdfjlkghdsf_drbarak'
    DEBUG = True
    MAX_CONTENT_PATH = 10000
    UPLOAD_FOLDER = '/home/drbarak/mysite/csv'


class Globals:
  app = None
