from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
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

#from prog.chatbot_init import p
import prog.routes, prog.chatbot, prog.chatbot_init  # leave here to prevent circular imports
prog.chatbot_init.init_chatbot()

#@app.route('/', methods=['GET', 'POST'])
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return prog.chatbot.chatbot()

import prog.game
prog.game.init_game()

@app.route('/', methods=['GET', 'POST'])
@app.route('/game', methods=['GET', 'POST'])
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

#@app.route('/', methods=['GET', 'POST'])
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
