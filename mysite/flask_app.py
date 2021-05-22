from flask import Flask, session
from globals import Config

app = Flask(__name__)
app.config.from_object(Config)

#echo > /var/log/drbarak.pythonanywhere.com.error.log

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
