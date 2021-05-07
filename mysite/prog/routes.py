from flask import render_template, flash, redirect, request, url_for
from werkzeug.utils import secure_filename
import os

from prog.forms import LoadForm, MainMenuForm, GetHashiNumberForm, CreateForm
from hashi import main
#from globals import Config, Globals

def main_menu(gui_class):
    global guiClass
    guiClass = gui_class

    form = MainMenuForm()
    if request.method == 'POST':
        if form.load.data:
            return redirect('/load')
        elif form.solve.data:
            return redirect('/getHnum')
        elif form.create.data:
            return redirect('/create')

        return redirect('/main_menu')
    return render_template('main_menu.html', title='Hashi Options', form=form)

def p(msg, msg2=''):
    guiClass.app.logger.warning(f'{msg} {msg2}')

def solve():
    form = GetHashiNumberForm()
    if request.method == 'POST':
#        p(f'output: {form.home.data} {form.solve.data} {form.hashi_num.data}')
        if form.home.data:
            return redirect('/main_menu')
        if form.solve.data:
            n = form.hashi_num.data
            p('number', n)
            if not(n == None or n in [0,1] or abs(n) > 32):
                result = main(guiClass, test=False, fileid=str(n))
                return f'''
                <!doctype html>
                    <body>
                        <h2>Hashi solution for puzzle {n}</h2>
                        <p></p>
                        <p><a href=https://www.pythonanywhere.com/user/drbarak/files{result[0]}>table</a></p>
                        <p><a href=https://www.pythonanywhere.com/user/drbarak/files{result[1]} >solution plot</a></p>
                        <p><a href=https://www.pythonanywhere.com/user/drbarak/files{result[2]}>solution page 1</a></p>
                        <p><a href=https://www.pythonanywhere.com/user/drbarak/files{result[3]}>solution page 2</a></p>
                        <p><a href=https://www.pythonanywhere.com/user/drbarak/files{result[4]}>solution page 3</a></p>
                        <p></p>
                        <p></p>
                        <p></p>
                        <p><a href="/">Click here to do it again</a>
                    </body>
                </html>
            '''#.format(result=result)
    return render_template('get_hashi_number.html', title='Hashi Options', form=form)

def create():
    form = CreateForm()
    if request.method == 'POST':
        if form.home.data:
            return redirect('/main_menu')
        if form.create.data:
            n = form.nrows.data
            p('number', n)
            if not(n == None or n < 2 or n > 20):
                flash(f'Ready to create table n={n}')

    return render_template('create.html', title='Create', form=form)

def load():
    form = LoadForm()
    if request.method == 'POST':
        if form.home.data:
            return redirect('/main_menu')
        if form.load.data and form.validate_on_submit() and form.file_name.data:
            file = form.file_name.data
            if file:
#                p(f'loading [{file.filename}]')
#                filename = secure_filename(file.filename)

                # generate local file name
                files = files_list()
                last_file = files[-1]
                p(last_file)
                file_id = int(last_file[5:6]) + 1  # all files start with 'Hashi'
                new_file = f'Hashi{file_id:02%d}{last_file[-4:]}'
                p(new_file)
#                file.save(os.path.join(guiClass.app.root_path, guiClass.app.config['UPLOAD_FOLDER'], new_file))
#                flash(f'file {filename} loaded')
#                p(f'loaded [{file.filename}]')

                return redirect('/display')
        flash(f'Failed loading the file - try again')

    return render_template('load.html', title='Load', form=form)

def files_list():
    base_dir = os.path.join(guiClass.app.root_path, guiClass.app.config['UPLOAD_FOLDER'])
    dir = os.walk(base_dir)
    file_list = []

    for path, subdirs, files in dir:
        for file in files:
            temp =  os.path.join(path + '/', file)
            file_list.append(file)
#            p(temp)
    file_list.sort()
    return(file_list)

def display_files():
    files = files_list()
    return render_template('display_files.html', hists=files)
#    return redirect('/main_menu')

