from flask import render_template, flash, redirect, request
from flask_app import app, session
from sqlalchemy import func
import os
import pandas as pd
import time
import numpy as np

from prog.forms import LoadForm, MainMenuForm, SolveForm, CreateForm
from hashi import main, sum_table, plot_table, clean_table, plot_trip
from globals import Globals

globals = Globals()

def p(msg=None, *args):
    try:
        if msg is None:
            app.logger.warning('')
            return
    except: # if there is an error (eg. msg is a DataFrame (on some version of pyhton) can not test for None)
        pass  # if the is an excpetion we know it is not None
    msg = f'{msg}'
    for k in args:
        msg = msg + f' {k}'
    app.logger.warning(msg)

def valid_user():
    return 'username_' in session and session['username_'] == 'admin_'

from flask_app import db, HashiDB, conn

def main_menu():
#    p('conn:', conn)
#        update()
    if globals.first:
        p()
        p('------------------------------')
        p('Start Hashi Web')
        globals.first = False
#        update()
    row = HashiDB.query.filter_by(id=45).first()
    if row is not None:
        db.session.delete(row)
    db.session.commit()
    form = MainMenuForm()
    if request.method == 'POST':
        if form.load.data:
            return redirect('/load')
        elif form.solve.data:
            return redirect('/solve')
        elif form.create.data:
            return redirect('/create')

        return redirect('/main_menu')
    return render_template('main_menu.html', title='Main Menu', form=form)

#import threading - can't be used on PythonAnywhere

def run_hashi(n):
    p('in run hashi: ', n)
    try:
#        result = main(test=False, fileid=str(n), WEB=True)
        result = read_from_db(n)
        if result is not None:
            result = main(test=False,  fileid=globals.df, WEB=True)
            p('in run hashi, after main: ', len(result), len(result[0]), len(result[1]))
    except Exception as e:
        result = [f'ERROR: {e} - report to support']
    if result == None:
        result = ['ERROR: invalid files - must be such that all nodes are connected']
    elif len(result) > 1:
        globals.f_id = n
        globals.table = result[0]
        globals.plot = result[1]
        globals.df_solution = result[2]
        result[2] = globals.df_solution.to_html()
        globals.steps = result[3]
        globals.step = -1
    error = result[0] if 'ERROR' in result[0] else ''
    return render_template('show_solution.html', title='Solution', n=n, error=error, data=result)
    '''
    result = [os.path.basename(r) for r in result[3]]
    if len(result) < 5:
        for i in range(len(result), 5):
            result.append('')
    root = 'http://drbarak.pythonanywhere.com/static/path/to/'
    '<p><a href=' + root + result[0] + '>table</a></p>'
    ''
    return f''
    <!doctype html>
        <body>
            {globals.df_solution}
            <p><a href="/">Click here to do it again</a>
        </body>
    </html>
    '''

root = '/home/drbarak/mysite/'
fname_ = f'{root}csv/Hashi'

def read_from_db(n):
    globals.f_id = n
    r = HashiDB.query.get(n)
    if r is not None:
        arr = np.frombuffer(bytes(r.data,'utf-8'), dtype='int8').reshape(r.cols, r.rows)
        p(f'data={r.id}, {r.cols}, {r.rows}, {r.sum}, {arr}')
        globals.ncols = r.cols
        globals.nrows = r.rows
        globals.df = pd.DataFrame(arr)
        p('OK')
    return r

def add_todb():
    arr = globals.df.to_numpy().astype('int8').tobytes()
    row = HashiDB(cols=int(globals.ncols), rows=int(globals.nrows), sum=int(globals.df.sum().sum()), data=arr)
    db.session.add(row)
    db.session.commit()
    p('new record', row.id)
    return row.id

def update():
    files = files_list()
    for new_file in files:
        error = ''
        file_to_read = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], new_file)
        try:
            hashi = pd.read_excel(file_to_read, header=None)
        except:
            try:
                hashi = pd.read_csv(file_to_read, header=None)
            except:
                error = 'ERROR load file: ' + file_to_read
        if error == '':
            globals.ncols = len(hashi.columns)
            globals.nrows = len(hashi.index)
            hashi = clean_table(hashi)
            if hashi is None:
                error = 'ERROR: table must be all numeric'
            else:
                globals.df = hashi.copy()
                p('OK:', file_to_read, globals.ncols, globals.nrows)
                add_todb()
        if error != '':
            p(error)
            break

def solve():  # load_internal
    form = SolveForm()
    error = ''
    if 'max' not in locals():
#        max = len(files_list())
#        max = db.session.query(HashiDB).count()  slower than the next query but faster then query.all
        max = db.session.query(func.count(HashiDB.id)).scalar()  # the fastest
    #        p(max)
    try:
        table_df = pd.read_sql_table("hashi", con=conn)
        df = table_df[table_df.columns[:3]]
        df = df.set_index('id')
    except:
        error = 'ERROR getting connection - try again later'
    if valid_user() and request.method == 'POST':
       #p(f'output: {form.home.data} {form.solve.data} {form.hashi_num.data}')
        if form.home.data:
            return redirect('/main_menu')
        if form.solve.data:
            n = form.hashi_num.data
            p('number', n)
            result = read_from_db(n)
            p(result)
            if result is not None:
                data = plot_table(globals.df, True)
                globals.table = data
                return render_template('show_only_table.html', title='Internal', nrows=globals.nrows, ncols=globals.ncols, data=data)
            error = 'ERROR: record not found'

           #if not(n == None or not n in [0,1] or abs(n) > max):
            if n in range(1, max + 1):
                fname = f'{fname_}{n:02}'
                f_name = f'{fname}.xlsx'
                hashi = None
                try:
                    hashi = pd.read_excel(f_name, header=None)
                except:
                    f_name = f'{fname}.csv'
                    try:
                        hashi = pd.read_csv(f_name, header=None)
                    except:
                        error = 'ERROR load file'
                if error == '':
                    globals.ncols = len(hashi.columns)
                    globals.nrows = len(hashi.index)
                    hashi = clean_table(hashi)
                    if hashi is None:
                        error = 'ERROR: table must be all numeric'
                    else:
                        globals.df = hashi.copy()
                        #p(hashi)
                        data = plot_table(hashi, True)
                        globals.table = data
                        #hashi = hashi.fillna('')
                        hashi.replace(0, '', inplace=True)
                        form = {}
                        for row in range(globals.nrows):
                          for col in range(globals.ncols):
                            val = hashi.iloc[row, col]
                            form[f'{row}_{col}'] = '' if val == '' else int(val)
                        p(form)
                        return render_template('show_only_table.html', title='Internal', nrows=globals.nrows, ncols=globals.ncols, form=form, data=data)
    return render_template('get_hashi_number.html', title='Internal', form=form, max=max, error=error, df=df.to_html())

def create():
    form = CreateForm()
    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/main_menu')
        if form.create.data:
            nrows = form.nrows.data
            ncols = form.ncols.data
            p('numbers', nrows, ncols)
            if not(nrows == None or nrows < 2 or nrows > 20) and not(ncols == None or ncols < 2 or ncols > 20):
#                p(f'Ready to create table n={n}')
                globals.nrows = nrows
                globals.ncols = ncols
                return redirect('/table')

    return render_template('create.html', title='Create', form=form)

def load():
    form = LoadForm()
    error = ''
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
                '''
                # test if it is a valid file
                try:
                    filestream = file
                    filestream.seek(0)
                    hashi = pd.read_csv(filestream, header=None)
                    #hashi = pd.DataFrame(ef)
                    p(hashi)
                    '''
                    p(file)
                    hashi = pd.DataFrame(file)
                    p(hashi)

                    milliseconds = int(round(time.time() * 1000))
                    tmp_file = f'Hashi{milliseconds}.csv'  # unique file name
                    file.save(tmp_file)
                    hashi=pd.read_cvs(tmp_file)
                    '''
                    result = main(test=True, fileid=hashi) # test = True so no plot of table is returned
                    p('result:', result)
                    error = ''
                except Exception as error:
                    p(error)
                    error = 'invalid file format or data'
                    return '''
                        <!doctype html>
                            <body>
                                <h2>Hashi upload new file - ERROR</h2>
                                <p></p>
                                <p>{error}</p>
                                <p></p>
                                <p><a href="/">Click here to continue</a>
                            </body>
                        </html>
                    '''.format(error=error)

                if result == None:  # invalid
                    try:
                        #os.remove(file_to_save)
                        #p('removed:', file_to_save)
                        error = 'Invalid data'
                    except Exception as error:
                        p("Error removing ", error)
                    p('err: ', error)
                else:
                    success, file_id = add_if_new(hashi)
                    if success:
                        return run_hashi(file_id)
                    error = file_id
        elif not form.validate_on_submit():
            error = 'wrong file type - must be CSV'
            p(error)
        #flash(f'Failed loading the file - try again')
    return render_template('load.html', title='Load', form=form, error=error)

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
    return render_template('display_files.html', hists=files)

def show_table():
    # remember that the form has action="/table_result" so when a key is pressed the routing is to table_result()
    return render_template('show_table.html', title='Show', nrows=globals.nrows, ncols=globals.ncols)

def steps():
    # remember that the form has action="/do_steps" so when a key is pressed the routing is to table_steps()
    p('in steps', request.method)
    if valid_user() and request.method == 'POST':
        form = request.form.to_dict(flat=False)
        if 'home' in form:
            return redirect('/main_menu')
    return render_template('step_solution.html', title='Steps', table=globals.table, df_solution=globals.df_solution.to_html(), n=globals.f_id)

def get_plot():
    if globals.step < 0:
        globals.table = plot_table(globals.df, WEB=True, partial=False)
    else:
#        l = {row.pair: row['#lines'] for i, row in globals.df_solution.iterrows() if i <= globals.step}
        # look for duplicates = 2 lines
        l = {}
        for i, row in globals.df_solution.iterrows():
            if i > globals.step: break
            if row.pair in l:
                l[row.pair] += 1
            else:  # check pair with exchange of nodes
                new_pair = (row.pair[1], row.pair[0])
                if new_pair in l:
                    l[new_pair] += 1
                else:
                    l[row.pair] = row['#lines']

        fig, ax = plot_table(globals.df, WEB=True, partial=True)
        globals.table = plot_trip(l, WEB=True, ax=ax, fig=fig)
    return

def do_steps():
    error = ''
    if valid_user() and request.method == 'POST':
        form = request.form.to_dict(flat=False)
        if 'home' in form:
            return redirect('/main_menu')
        if 'next' in form:
            if globals.step < len(globals.df_solution) - 1:
                globals.step += 1
                get_plot()
            else:
                error = 'DONE: All connected properly'

        elif 'prev' in form:
            if globals.step >= 0:
                globals.step -= 1
                get_plot()
    if error == '':
        error = f'Step: {globals.step}' if globals.step >= 0 else ''
    return render_template('step_solution.html', title='Steps', form=form, table=globals.table, df_solution=globals.df_solution.to_html(), n=globals.f_id, error=error)


def table_result():
    if valid_user() and request.method == 'POST':
        form = request.form.to_dict(flat=False)
        if 'home' in form:
            return redirect('/main_menu')
        if 'save' in form or 'solve' in form:
            if 'solve' in form:
                title = 'Internal'
                hashi = globals.df
                return run_hashi(globals.f_id)
            del form['save']
            title = 'Show'
            error = ''
            hashi = None
            err = 0
            try:
                #p('form is:', form)
                df = pd.DataFrame(form)
                #p('df is:', df)
                a = df.to_numpy()
                b = a.reshape(globals.nrows, globals.ncols)
                hashi = pd.DataFrame(b)
                err = 1
                hashi.replace(' ', 0, inplace=True)
                hashi.fillna(0, inplace=True, downcast='infer')
                hashi = hashi.apply(pd.to_numeric, downcast='integer')
            except Exception as e:
                p(f'except: {e}')
                if err == 0: error = 'ERROR: could not convert to dataFrame'
                elif err == 1: error = 'ERROR: all data must be numeric integer'
                else: error = f'err={err}'
                p('error: ', error)
            p(hashi)
            if error == '':
                if ((hashi < 0) | (hashi > 8)).sum().sum() > 0:
                    error = 'ERROR: all numbers can not be less than 0 or greater than 8'
                else:
                    score = sum_table(hashi)
                    if score <= 2:
                        error = f'ERROR: not enough data score={score}'
                    elif score % 2:
                        error = f'ERROR: sum of all data must be even (multiple of 2) and not {score}'
                    else:
                        try:
                            # remove last cols and rows if they are all 0
                            while hashi.tail(1).to_numpy().sum() == 0:
                                hashi.drop(hashi.tail(1).index,inplace=True)
                            while hashi[hashi.columns[-1]].sum() == 0:
                                hashi = hashi[hashi.columns[:-1]]

                            result = main(test=False, fileid=hashi)
                        except:
                            p('exception during main - need to check hashi.py')
                            result = None
                        if result == None:  # invalid
                            error = 'ERROR: invalid data - must be such that all islands are connected'
                            '''
                            milliseconds = int(round(time.time() * 1000))
                            tmp_file = f'Hashi{milliseconds}.csv'  # unique file name
                            file_to_save = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], tmp_file)
                            hashi.to_csv(file_to_save, header=False, index=False)
                            p(tmp_file)
                            '''
                            p(error)
                        else:
                            #new_file, file_id, file_to_save = get_new_name()
                            success, file_id = add_if_new(hashi)
                            if success:
                                return run_hashi(file_id)
                            error = file_id
                            '''
                            try:
                                hashi.to_csv(file_to_save, header=False, index=False)
                            except:
                                error = f'file {new_file} write ERROR'
                                p(f'error [{file_to_save}]')
                            '''
#            p('rows', globals.nrows)
            return render_template('show_table.html', title=title, nrows=globals.nrows, ncols=globals.ncols, error=error, form=form)

    return redirect('/main_menu')

def add_if_new(hashi):
    # verify puzzle not already in db
    arr = hashi.to_numpy().astype('int8').tobytes()
    exist = HashiDB.query.filter_by(cols=len(hashi.columns), rows=len(hashi.index), sum=int(hashi.sum().sum()), data=arr).first()
    if exist is None:
        globals.ncols = len(hashi.columns)
        globals.nrows = len(hashi.index)
        globals.df = hashi
        file_id = add_todb()
        return True, file_id
    return False, f'ERROR: puzzle already exists id={exist.id}'

