from flask import Flask, session
from globals import Config

app = Flask(__name__)
app.config.from_object(Config)

import prog.routes

@app.route('/', methods=['GET', 'POST'])
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

@app.route('/display')
def display_files():
    return prog.routes.display_files()

@app.route('/table')
def show_table():
    return prog.routes.show_table()

@app.route('/table_result', methods=['GET', 'POST'])
def table_result():
   return prog.routes.table_result()