from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from globals import Config

app = Flask(__name__)
app.config.from_object(Config)

#echo > /var/log/drbarak.pythonanywhere.com.error.log

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="drbarak",
    password="shushu1952",
    hostname="drbarak.mysql.pythonanywhere-services.com",
    databasename="drbarak$hashi",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
#db.session.expire_on_commit = False
conn = db.engine.connect()

db.app = app
db.init_app(app)
engine_container = db.get_engine(app)

def cleanup(session):
    """
    This method cleans up the session object and also closes the connection pool using the dispose method.
    """
    session.close()
    engine_container.dispose()

class HashiDB(db.Model):

    __tablename__ = "hashi"

    id = db.Column(db.Integer, primary_key=True)
    cols = db.Column(db.Integer)
    rows = db.Column(db.Integer)
    sum = db.Column(db.Integer)
    data = db.Column(db.Text)
    future1 = db.Column(db.Integer)
    future2 = db.Column(db.Integer)
    future3 = db.Column(db.Text)

class BotDB(db.Model):

    __tablename__ = "chatbot"

    id = db.Column(db.Integer, primary_key=True)
    db_chat = db.Column(db.Text)
    '''
    # open MySQL Bash console
    use drbarak$hashi;
    show tables;
    drop table chatbot;
    create table chatbot(id int NOT NULL AUTO_INCREMENT, db_chat blob, PRIMARY KEY (id));
    '''

class GameDB(db.Model):

    __tablename__ = "game"

    id = db.Column(db.Integer, primary_key=True)
    db_chat = db.Column(db.Text)
    '''
    create table game(id int NOT NULL, db_chat blob, PRIMARY KEY (id));
    select * from game;
    delete from game;
    '''


class hallDB(db.Model):

    __tablename__ = "hall"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer)
    name = db.Column(db.String(255))
    picture = db.Column(db.String(255))
    directions = db.Column(db.String(255))
    '''
CREATE TABLE hall(
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,             /* קוד אולם (ללקוח יכולים להיות מספר אולמות, כגון מספר אולמות במיתח */
    client_id INT,                           /*  קוד לקוח (הלקוחות מנוהלים במערכת המרכזית) */
    name VARCHAR(255) NOT NULL DEFAULT '',  /*  שם אולם */
    picture BLOB,                           /* תמונת המקום  */
    picture_url VARCHAR(255),
    directions VARCHAR(255)                 /*  דרכי הגעה */
    );
    '''

class zoneDB(db.Model):

    __tablename__ = "zone"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    hall_id = db.Column(db.Integer)
    client_id = db.Column(db.Integer)
    marked_seats = db.Column(db.Boolean)
    max_seats = db.Column(db.Integer)
    '''
CREATE TABLE zone(
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,             /* קוד איזור */
    name VARCHAR(255) NOT NULL DEFAULT '',                  /* שם איזור (יציע, אולם, VIP וכד') */
    hall_id INT,
    client_id INT,
    marked_seats TINYINT,                            /* מקומות משוריינים/חופשיים */
    max_seats INT,                                           /* מיכסה מירבית */
    FOREIGN KEY(hall_id) REFERENCES hall(id) ON DELETE CASCADE
    );
    '''
class seatDB(db.Model):

    __tablename__ = "seat"

    zone_id = db.Column(db.Integer, primary_key=True)
    hall_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, primary_key=True)
    row = db.Column(db.Integer, primary_key=True)
    seat = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Boolean)
    '''
CREATE TABLE seat(
    zone_id INT NOT NULL PRIMARY KEY,
    hall_id INT,
    client_id INT,
    row INT,
    seat INT,
    status TINYINT,
    FOREIGN KEY(zone_id) REFERENCES zone(id) ON DELETE CASCADE,
    FOREIGN KEY(hall_id) REFERENCES hall(id) ON DELETE CASCADE
    );
    '''

class userDB(db.Model):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), default='')
    ip_address = db.Column(db.String(20))
    insert_dt = db.Column(db.DateTime, server_default=func.now())
    log = db.Column(db.Boolean, default=True)
    '''
CREATE TABLE `user_login` (
    `id` int unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT '',
    `ip_address` varchar(20) DEFAULT NULL,
    `insert_dt` datetime NOT NULL DEFAULT NOW(),
    `update_dt` timestamp ON UPDATE CURRENT_TIMESTAMP,
    log TINYINT NOT NULL DEFAULT False,
    UNIQUE KEY `ip` (`ip_address`)
);
    '''

class user_loginDB(db.Model):

    __tablename__ = "user_login"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    login_dt = db.Column(db.DateTime, server_default=func.now())
    '''
CREATE TABLE `user_login` (
  `id` int unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id int unsigned NOT NULL,
  `login_dt` datetime NOT NULL DEFAULT NOW(),
  FOREIGN KEY(user_id) REFERENCES user(id),
);
    '''

class logDB(db.Model):

    __tablename__ = "log"

    id = db.Column(db.Integer, primary_key=True)
    login_dt = db.Column(db.DateTime, server_default=func.now())
    line = db.Column(db.String(255))

import prog.routes, prog.chatbot, prog.chatbot_init, prog.cartisan  # leave here to prevent circular imports

# ---------- game ---------------
import prog.game
prog.game.init_game()

@app.route('/game_1986', methods=['GET', 'POST'])
def game():
    return prog.game.home()
@app.route('/help')
def help():
    return prog.game.help()
@app.route('/join_game/')
def join_game():
    return prog.game.join_game()
@app.route('/create_game/<int:level>')
def create_game(level):
    return prog.game.create_game(level)
@app.route('/start_game/<int:game_code>/<int:player>')
def start_game(game_code, player):
    return prog.game.start_game(game_code, player)
@app.route('/wait_for_joining/<int:game_code>/<int:player>')
def wait_for_joining(game_code, player):
    return prog.game.wait_for_joining(game_code, player)
@app.route('/join_validation/')
def join_validation_():
    return prog.game.join_validation(0)
@app.route('/join_validation/<int:game_code>')
def join_validation(game_code):
    return prog.game.join_validation(game_code)
@app.route('/wait_for_game_start/<int:game_code>/<int:player>')
def wait_for_game_start(game_code, player):
    return prog.game.wait_for_game_start(game_code, player)
@app.route('/show_question/<int:game_code>/<int:player>')
def show_question(game_code, player):
    return prog.game.show_question(game_code, player)
@app.route('/get_answer/<int:game_code>/<int:player>/<int:answer>')
def get_answer(game_code, player, answer):
    return prog.game.get_answer(game_code, player, answer)
@app.route('/wait_for_answers/<int:game_code>/<int:player>')
def wait_for_answers(game_code, player):
    return prog.game.wait_for_answers(game_code, player)
@app.route('/wait_for_other_answers/<int:game_code>/<int:player>')
def wait_for_other_answers(game_code, player):
    return prog.game.wait_for_answers(game_code, player, True)

# ---------- chatbot ---------------
prog.chatbot_init.init_chatbot()

#@app.route('/', methods=['GET', 'POST'])
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return prog.chatbot.chatbot()

# ---------- hashi ---------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/hashi', methods=['GET', 'POST'])
@app.route('/main_menu', methods=['GET', 'POST'])
def main_menu():
    if 'init_' not in session:
        session['init_'] = 'init_'
        session['username_'] = 'admin_'
    return prog.routes.main_menu()

@app.route('/create', methods=['GET', 'POST'])
def create():
    return prog.routes.create()

@app.route('/load', methods=['GET', 'POST'])
def load():
    return prog.routes.load()

@app.route('/solve', methods=['GET', 'POST'])
def solve():
    return prog.routes.solve()

@app.route('/table')
def show_table():
    return prog.routes.show_table()

# comes from action="" in show_table.html, show_only_table
@app.route('/table_result', methods=['GET', 'POST'])
def table_result():
   return prog.routes.table_result()

# comes from action="" in show_solution.html
@app.route('/steps', methods=['GET', 'POST'])
def steps():
   return prog.routes.steps()

# comes from action="" in step_solution.html
@app.route('/do_steps', methods=['GET', 'POST'])
def do_steps():
   return prog.routes.do_steps()

# not used in the prog - to be able to enter in manually in the url - it is called internally after show_table()
@app.route('/display')
def display_files():
    return prog.routes.display_files()


# ---------- cartisan ---------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/cartisan', methods=['GET', 'POST'])
def cartisan():
    if 'init_' not in session:
        session['init_'] = 'init_'
        session['username_'] = 'admin_'
    return prog.cartisan.main_menu()

@app.route('/hall', methods=['GET', 'POST'])
def hall():
    return prog.cartisan.hall()

@app.route('/zone', methods=['GET', 'POST'])
def zone():
    return prog.cartisan.zone()

@app.route('/seat', methods=['GET', 'POST'])
def seat():
    return prog.cartisan.seat()

@app.route('/cartisan_load', methods=['GET', 'POST'])
def cartisan_load():
    return prog.cartisan.load()


