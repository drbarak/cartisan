import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'asdfjlkghdsf_drbarak'
    DEBUG = False
    UPLOAD_FOLDER ='/home/drbarak/mysite/csv'
    ALLOWED_EXTENSIONS = {'csv'}

class Globals:
    nrows = 0
    ncols = 0
    f_id = 0
    df = None
    log_file = 'hashi.log'
    table = None
    plot = None
    df_solution = None
    step = -1
    steps = None
    first = True
    games = {}
    active_games = 0