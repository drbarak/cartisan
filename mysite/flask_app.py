from flask import Flask
from globals import Config, Globals

app = Flask(__name__)
app.config.from_object(Config)

myGlobal = Globals()
myGlobal.app = app

import prog.routes

@app.route('/', methods=['GET', 'POST'])
@app.route('/main_menu', methods=['GET', 'POST'])
def main_menu():
    return prog.routes.main_menu(myGlobal)

@app.route('/create', methods=['GET', 'POST'])
def create():
    return prog.routes.create()

@app.route('/load', methods=['GET', 'POST'])
def load():
    return prog.routes.load()

@app.route('/getHnum', methods=['GET', 'POST'])
def solve():
    return prog.routes.solve()

@app.route('/display')
def display_files():
    return prog.routes.display_files()
