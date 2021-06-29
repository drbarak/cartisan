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

import prog.routes, prog.chatbot, prog.chatbot_init  # leave here to prevent circular imports
prog.chatbot_init.init_chatbot()

@app.route('/', methods=['GET', 'POST'])
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return prog.chatbot.chatbot()

#@app.route('/', methods=['GET', 'POST'])
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
