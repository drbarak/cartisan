from flask import render_template, flash, redirect, request
from flask_app import app, session
import os
import pandas as pd

from prog.forms import LoadForm, MainMenuForm, SolveForm, CreateForm
from hashi import main, sum_table
from globals import Globals

globals = Globals()

def p(msg, msg2=''):
    app.logger.warning(f'{msg} {msg2}')
def valid_user():
    return 'username_' in session and session['username_'] == 'admin_'

def main_menu():
    form = MainMenuForm()
    if request.method == 'POST':
        if form.load.data:
            return redirect('/load')
        elif form.solve.data:
            return redirect('/solve')
        elif form.create.data:
            return redirect('/create')

        return redirect('/main_menu')
    return render_template('main_menu.html', title='Hashi Options', form=form)

def run_hashi(n):
    result = main(test=False, fileid=str(n))
    if result == None:
        result = ['Error']
    p(result)
    if len(result) < 5:
        for i in range(len(result), 5):
            result.append('x')
    return  f'''
    <!doctype html>
        <body>
            <h2>Hashi solution for puzzle {n} t4</h2>
            <p>[{result[0]}, {result[1]}, {result[2]}, {result[3]}]</p>
            <p><a href=http://drbarak.pythonanywhere.com/Hashi_table.png>table</a></p>
            <p><a href=/home/drbarak/mysite/Hashi_table.png>solution plot</a></p>
            <p><a href=https://www.pythonanywhere.com/user/drbarak[/home/drbarak/mysite/png/Hashi_table.png>solution page 1</a></p>
            {'' if result[3] == ''  else
                '<p><a href=/home/drbarak/mysite/Hashi_table.png>solution page 2</a></p>'
            }
            {'' if result[4] == ''  else
                '<p><a href=https://www.pythonanywhere.com/user/drbarak/{result[0]}>solution page 3</a></p>'
            }
            <p></p>
            <p></p>
            <p></p>
            <p><a href="/">Click here to do it again</a>
        </body>
    </html>
    '''#.format(result=result)


def solve():
    form = SolveForm()
    if 'max' not in locals():
        max = len(files_list())
    if valid_user() and request.method == 'POST':
       #p(f'output: {form.home.data} {form.solve.data} {form.hashi_num.data}')
        if form.home.data:
            return redirect('/main_menu')
        if form.solve.data:
            n = form.hashi_num.data
            p('number', n)
            if not(n == None or n in [0,1] or abs(n) > max):
                return run_hashi(n)
    return render_template('get_hashi_number.html', title='Hashi Options', form=form, max=max)

def create():
    form = CreateForm()
    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/main_menu')
        if form.create.data:
            n = form.nrows.data
            p('number', n)
            if not(n == None or n < 2 or n > 20):
                p(f'Ready to create table n={n}')
                globals.nrows = n
                return redirect('/table')

    return render_template('create.html', title='Create', form=form)

def load():
    form = LoadForm()
    if valid_user() and request.method == 'POST':

        if form.home.data:
            return redirect('/main_menu')
        if form.load.data and form.validate_on_submit() and form.file_name.data:
            file = form.file_name.data
            if file:
                #p(f'loading [{file.filename}]')
                #filename = secure_filename(file.filename)
                '''
                    to make sure not 2 users at the same time
                    we need to write a file in a mode that writes only if does not exists
                    if error - we try over and over until successful
                    once we finished checking the new file we delete the lock file and now we can read
                    the list of iles
                    when we are locked, we should check date & time of the file - if it is older than 10 seconds
                    we assume it is left from an aborted process and we delete it
                '''
                new_file, file_id, file_to_save = get_new_name()
                try:
                    file.save(file_to_save)
                   #flash(f'Checking the file - Please wait')
                except:
                    flash(f'file {file.filename} write ERROR')
                    p(f'error [{file_to_save}]')
                # test if it is a valid file
                result = main(test=False, fileid=str(file_id))
                p('result:', result)
                error = ''
                if result == None:  # invalid
                    try:
                        os.remove(file_to_save)
                        p('removed:', file_to_save)
                    except Exception as error:
                        p("Error removing ", error)
                    return '''
                    <!doctype html>
                        <body>
                            <h2>Hashi upload new file - ERROR</h2>
                            <p></p>
                            <p>{form.error}</p>
                            <p>{error[0]}</p>
                            <p></p>
                            <p><a href="/">Click here to continue</a>
                        </body>
                    </html>
                '''.format(error=error)

                return redirect('/display')
        flash(f'Failed loading the file - try again')

    return render_template('load.html', title='Load', form=form)

def get_new_name():
        # generate local file name
    files = files_list()
    last_file = files[-1]
   #p(last_file)
    file_id = int(last_file[5:7]) + 1  # all files start with 'Hashi'
    new_file = f'Hashi{file_id:02}{last_file[-4:]}'
    file_to_save = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], new_file)
    p(f'new: {new_file} [{file_to_save}]')
    return new_file, file_id, file_to_save

def files_list():
    base_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    dir = os.walk(base_dir)
    file_list = []

    for path, subdirs, files in dir:
        for file in files:
           #temp =  os.path.join(path + '/', file)
            file_list.append(file)
            #p(temp)
    file_list.sort()
    return(file_list)

def display_files():
    files = []
    if valid_user():
        files = files_list()
    return render_template('table.html', hists=files)

def show_table():
#    p('in show_table', globals.nrows)
    return render_template('show_table.html', title='Show', nrows=globals.nrows)

def table_result():
#    return prog.routes.table_result()
    if valid_user() and request.method == 'POST':
        form = request.form.to_dict(flat=False)
        if 'home' in form:
            return redirect('/main_menu')
        if 'save' in form:
            del form['save']
            error = ''
            hashi = None
            err = 0
            try:
                #p('form is:', form)
                df = pd.DataFrame(form)
                n = globals.nrows
                a = df.to_numpy()
                b = a.reshape(n,n)
                hashi = pd.DataFrame(b)
                err = 1
                hashi.replace(' ', 0, inplace=True)
                hashi.fillna(0, inplace=True, downcast='infer')
                hashi = hashi.apply(pd.to_numeric, downcast='integer')
            except Exception as e:
                p(f'except {e}')
                if err == 0: error = 'ERROR: could not convert to dataFrame'
                elif err == 1: error = 'ERROR: all data must be numeric integer'
                else: error = f'err={err}'
                p('error', error)
            p(hashi)
            if error == '':
                if ((hashi < 0) | (hashi > 8)).sum().sum() > 0:
                    error = 'ERROR: all numbers can not be less than 0 or greater than 8'
                else:
                    score = sum_table(hashi)
                    if score <= 2:
                        error = f'ERROR: not enough data score={score}'
                    elif score % 2:
                        error = f'ERROR: sum of all data must be even (multiple of 2) score={score}'
                    else:
                        result = main(test=False, fileid=hashi)
                        if result == None:  # invalid
                            #os.remove(file_to_save)
                            pass
                        else:
                            new_file, file_id, file_to_save = get_new_name()
                            try:
                                hashi.to_csv(file_to_save, header=False, index=False)
                                return run_hashi(file_id)
                            except:
                                flash(f'file {new_file} write ERROR')
                                p(f'error [{file_to_save}]')
#            p('rows', globals.nrows)
            return render_template('show_table.html', title='Show3', nrows=globals.nrows, error=error, form=form)

    return render_template('show_table.html', title='Result', nrows=globals.nrows)


