# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request
from flask_app import session, app
#from sqlalchemy import func
import os #תsys
import pandas as pd
import time
#import numpy as np

from prog.forms import CartisanForm, Cartisan_hallForm, Cartisan_LoadForm, Cartisan_zoneForm, Cartisan_seatForm
from globals import Globals
from hashi import val
from prog.chatbot_init import p, send_email

globals = Globals()

def valid_user():
    return 'username_' in session and session['username_'] == 'admin_'

from flask_app import db, hallDB, zoneDB, seatDB, user_loginDB

IDLE_TIME = 60 * 60 # max 1 hourד betweene mail messages - need to close the app and start again after an hour

def clear_session():
        session.pop('chat_', '')
        session.pop('user_msg', '')
        session.pop('url_icon', '')
        session.pop('df_id', '')
        session.pop('switched_lang', '')
        session.pop('google', '')
        session.pop('index', '')
        session.pop('clear', '')
        session.pop('debug', '')
        session.pop('lang', '')
        session.pop('new_lang', '')
        session.pop('mobile', '')
        session.pop('error', '')
        session.pop('RUN_TEST', '')
        session.pop('player', '')
        session.pop('game_code', '')
        session.pop('YES_NO', '')
        session.pop('game_', '')
        session.pop('yes_addition', '')

        base_dir = os.path.join(app.root_path, 'static')
        file = base_dir + '/mylog.true'
        session['mylog'] = True if os.path.exists(file) else False

        p(session)

        delta = time.time() - session['time'] if 'time' in session else 3600   # do it no more than once an hour for the same user
        if delta > IDLE_TIME and \
            request.headers['X-Real-IP'] not in ['82.81.245.207', '50.17.220.95', '5.29.160.29', '54.226.94.43'] : # dr barak ip - no need to get a notice each time I log in

            p(session)

            row = user_loginDB(ip_address=request.headers['X-Real-IP'])
            try:
                db.session.add(row)
                db.session.commit()
                if row.id is None:
                    p('error adding user_login')
                else:
                    p('New user_login id=', row.id, 'ip=', row.ip_address)
            except Exception as err:
                p(err)
                pass

            send_email(text='Message from Cartisan',ip = request.headers['X-Real-IP'], src='Cartisan')
        else:
            p('delta time=', round(delta, 0) , request.headers['X-Real-IP'], request.headers['X-Forwarded-For'])

def main_menu():
    #p('cartisan main_menu', session)
    if 'cartisan_' not in session:
        p('------------------------------')
        #p(session)
        session['cartisan_'] = 'cartisan_'
        session['time'] = time.time()
        clear_session()
        p('Start Cartisan')
    else:
        if 'time' in session:
            session_time = session['time']
            delta = time.time() - session_time
            if delta > IDLE_TIME:
                p('reset time', delta > IDLE_TIME)
                clear_session()
                session['time'] = time.time()
            else:  # reset the session time as long as no delay of more than idle_time
                session['time'] = time.time()
        else:
            session['time'] = time.time()
            clear_session()
    '''
    row = HashiDB.query.filter_by(id=45).first()
    if row is not None:
        db.session.delete(row)
    db.session.commit()
    '''
    session['picture'] = ''
    form = CartisanForm()
    if request.method == 'POST':
        if form.hall.data:
            return redirect('/hall')
        elif form.zone.data:
            return redirect('/zone')
        elif form.seat.data:
            return redirect('/seat')

        return redirect('/cartisan')
    return render_template('cartisan_main_menu.html', title='כרטיסן', form=form)

#import threading - can't be used on PythonAnywhere

picture_dir = 'pictures/'
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024   # max file size 160 KB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hall():
    form = Cartisan_hallForm()
    df_chat_html = df_chat = error = ''
    hall_id = name = directions = url_icon = ''
    picture = session['picture']
    if valid_user() and request.method == 'POST':
        if form.home.data:
            session['picture'] = ''
            return redirect('/cartisan')
        if form.hall_list.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
             #hall_id = form.hall_id.data
            #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            else:
                df = read_from_hall_db(client_id, None)
                if df is not None:
                    df_chat = df
                    df_chat_html = (df_chat.style
                      .set_properties(subset=['id$'], **{'font-weight': 'bold'})
                      .set_properties(subset=['name$'], **{'width': '500px'})
                      .set_properties(subset=['id$'], **{'width': '20px'})
                      .set_properties(**{'text-align': 'left'})
                      .set_table_styles([dict(selector = 'th', props=[('text-align', 'left')])])
                      .hide_index()
                      .render()
                      .replace('name$','שם אולם')
                      .replace('id$','קוד אולם')
                      )
                else:
                    error = 'לא נמצאו אולמות'

        if form.search.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
             #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20) or (hall_id == None or hall_id < 1):
                error = 'קוד לקוח או קוד אולם אינו תקין'
            else:
                r = read_from_hall_db(client_id, hall_id)
                if r is not None:
                    name = r.name if r.name is not None else ''
                    picture = r.picture if r.picture is not None else ''
                    directions = r.directions if r.directions is not None else ''
                    url_icon = picture_dir + picture if picture != '' else ''
                    session['picture'] = ''
                else:
                    error = 'אולם לא נמצא'


        if form.update.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1:
                error = 'קוד לקוח או קוד אולם אינו תקין'
            else:
                r = read_from_hall_db(client_id, hall_id)
                if r is not None:
                    name = r.name = form.name.data
                    picture = r.picture = form.picture.data
                    directions = r.directions = form.directions.data
                    url_icon = picture_dir + picture if picture != '' else ''
                    db.session.commit()
                    session['picture'] = ''

        if form.create.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif (hall_id != '' and hall_id is not None):
                #p('id = [', hall_id ,']')
                error = 'קוד אולם חייב להיות ריק - המערכת תעדכן את קוד האולם החדש'
            else:
                row = hallDB(client_id=client_id, name=form.name.data, picture=form.picture.data, directions=form.directions.data)
                db.session.add(row)
                db.session.commit()
                if row.id is None:
                    error = 'תקלה בהוספת אולם'
                else:
                    hall_id = form.hall_id.data = row.id
                    error = 'קוד אולם חדש'
                    name = form.name.data
                    picture = form.picture.data
                    directions = form.directions.data
                    url_icon = picture_dir + picture if picture != '' else ''
                    session['picture'] = ''

        if form.delete.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            if (hall_id == '' or hall_id is None):
                error = 'יש לספק קוד אולם'
            else:
                row = read_from_hall_db(client_id, hall_id)
                if row.id is None:
                    error = 'אולם לא נמצא - לא ניתן למחיקה'
                else:
                    db.session.delete(row)
                    db.session.commit()
                    if row.id is None:
                        error = 'תקלה במחיקת אולם'
                    else:
                        form.hall_id.data = row.id
                        error = 'אולם נמחק'
                        session['picture'] = ''

        if form.load.data:
            picture = form.picture.data
            if picture == '' or picture is None:
                error = 'שם קובץ תמונה לא תקין'
            else:  # make sure a file with than name does not exists
                base_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                file = base_dir + '/' + picture
                #p(file)
                if os.path.exists(file):
                    error = 'קובץ כבר קיים'
                else:
                    session['picture'] = picture
                    return redirect('/cartisan_load')

    return render_template('cartisan_hall.html', title='אולמות',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), name=name, picture=picture, directions=directions, url_icon=url_icon, hall_id=hall_id
        )

def read_from_hall_db(client_id, hall_id):
    if hall_id is None: # search by client_id
        result = hallDB.query.filter_by(client_id=client_id).all()
        #p(result)
        if result is not None:
            hall_list = []
            for r in result:
                #p(f'data={r.id}, {r.client_id}, {r.name}, {r.picture}, {r.directions}')
                hall_list.append([r.id, r.name])
            #p('OK')
            df_chat = pd.DataFrame(hall_list, columns=['id$', 'name$'])
            #p(df_chat)
            return(df_chat)
    else:
        result = hallDB.query.get(hall_id)
    return result

def load():
    form = Cartisan_LoadForm()
    error = ''
    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/hall')

        if form.load.data and form.file_name.data:
            if form.validate_on_submit():
                file = form.file_name.data
                if file and allowed_file(file.filename):
                    picture=session['picture']
                    filename = secure_filename(picture)
                    base_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                    p(os.path.join(base_dir, filename))
                    file.save(os.path.join(base_dir, filename))
                    return redirect('/hall')
                else:
                    error = 'שגיאה בסוג הקובץ - חייב להיות קובץ תמונה'
            else:
                error = 'שגיאה בסוג הקובץ - חייב להיות קובץ תמונה'
        elif form.load.data and not form.file_name.data:
            error = 'לא נבחר קובץ'
            p(error)
        elif form.load.data and not form.validate_on_submit():
            error = 'שגיאה בסוג הקובץ - חייב להיות קובץ תמונה'
            p(error)
    return render_template('cartisan_load.html', form=form, error=error)

def zone():
    form = Cartisan_zoneForm()
    df_chat_html = df_chat = error = ''
    hall_id = name = marked_seats = max_seats = zone_id = ''
    marked_seats= False
    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/cartisan')
        if form.zone_list.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif (val(hall_id) < 1):
                error = 'קןד אולם אינו תקין'
            else:
                df = read_from_zone_db(client_id, hall_id, None)
                if df is not None:
                    df_chat = df
                    df_chat_html = (df_chat.style
                      .set_properties(subset=['id$'], **{'font-weight': 'bold'})
                      .set_properties(subset=['name$'], **{'width': '500px'})
                      .set_properties(subset=['id$'], **{'width': '20px'})
                      .set_properties(**{'text-align': 'left'})
                      .set_table_styles([dict(selector = 'th', props=[('text-align', 'left')])])
                      .hide_index()
                      .render()
                      .replace('name$','שם אזור')
                      .replace('id$','קוד אזור')
                      )
                else:
                    error = 'לא נמצאו אזורים'

        if form.search.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור אינו תקין'
            else:
                r = read_from_zone_db(client_id, hall_id, zone_id)
                if r is not None:
                    #p(r, r.name, r.id, r.marked_seats)
                    name = r.name if r.name is not None else ''
                    marked_seats = r.marked_seats if r.marked_seats is not None else ''
                    max_seats = r.max_seats if r.max_seats is not None else ''
                else:
                    error = 'אזור לא נמצא'

        if form.update.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור אינו תקין'
            else:
                r = read_from_zone_db(client_id, hall_id, zone_id)
                if r is not None:
                    name = r.name = form.name.data
                    marked_seats = r.marked_seats = form.marked_seats.data if form.marked_seats.data is not None else ''
                    max_seats = r.max_seats = form.max_seats.data if val(form.max_seats.data) > 0 else ''
                    db.session.commit()

        if form.create.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif val(hall_id) < 1:
                error = 'קוד אולם אינו תקין'
            elif (zone_id != ''):
                error = 'קוד אולם חייב להיות ריק - המערכת תעדכן את קוד האזור החדש'
            else:
                #p('id = [', zone_id ,']')
                max_seats = form.max_seats.data if val(form.max_seats.data) > 0 else ''
                marked_seats = form.marked_seats.data if form.marked_seats.data is not None else ''
                row = zoneDB(client_id=client_id, hall_id=hall_id, name=form.name.data, marked_seats=marked_seats, max_seats=max_seats)
                try:
                    db.session.add(row)
                    db.session.commit()
                    if row.id is None:
                        error = 'תקלה בהוספת אזור'
                    else:
                        zone_id = form.zone_id.data = row.id
                        error = 'קוד אזור חדש'
                        name = form.name.data
                except Exception as err:
                    p(err)
                    error = 'שגיאה בהוספת אזור - יתכן שקוד האולם אינו קיים'
                    pass

        if form.delete.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            if (zone_id == ''):
                error = 'יש לספק קוד אזור'
            else:
                row = read_from_zone_db(client_id, hall_id, zone_id)
                if row is None or row.id is None:
                    error = 'אזור לא נמצא - לא ניתן למחיקה'
                else:
                    db.session.delete(row)
                    db.session.commit()
                    if row.id is None:
                        error = 'תקלה במחיקת אזור'
                    else:
                        form.zone_id.data = row.id
                        error = 'אזור נמחק'

    return render_template('cartisan_zone.html', title='אולמות',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), name=name, marked_seats=marked_seats, max_seats=max_seats, zone_id=zone_id, hall_id=hall_id
        )

def read_from_zone_db(client_id, hall_id, zone_id):
    if zone_id is None: # search by client_id and hall_id
        result = zoneDB.query.filter_by(client_id=client_id, hall_id=hall_id).all()
        #p(result)
        if result is not None:
            zone_list = []
            for r in result:
                #p(f'data={r.id}, {r.client_id}, {r.name}, {r.picture}, {r.directions}')
                zone_list.append([r.id, r.name])
            #p('OK')
            df_chat = pd.DataFrame(zone_list, columns=['id$', 'name$'])
            #p(df_chat)
            return(df_chat)
    else:
        result = zoneDB.query.get(zone_id)
    return result

def seat():
    form = Cartisan_seatForm()
    df_chat_html = df_chat = error = ''
    hall_id = row = seat = zone_id = ''
    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/cartisan')
        if form.seat_list.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif (val(hall_id) < 1):
                error = 'קןד אולם אינו תקין'
            elif (val(zone_id) < 1):
                error = 'קןד אזור אינו תקין'
            else:
                df = read_from_seat_db(client_id, hall_id, zone_id, None, None)
                if df is not None:
                    df_chat = df
                    df_chat_html = (df_chat.style
                      .set_properties(subset=['id$'], **{'font-weight': 'bold'})
                      .set_properties(subset=['name$'], **{'width': '500px'})
                      .set_properties(subset=['id$'], **{'width': '20px'})
                      .set_properties(**{'text-align': 'left'})
                      .set_table_styles([dict(selector = 'th', props=[('text-align', 'left')])])
                      .hide_index()
                      .render()
                      .replace('name$','כסא')
                      .replace('id$','שורה')
                      )
                else:
                    error = 'לא נמצאו מושבים'

        if form.search.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            row = form.row.data
            if row is None: row = ''
            seat = form.seat.data
            if seat is None: seat = ''
            #p('numbers', client_id, hall_id)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1 or val(row) < 1 or val(seat) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור או מספר שורה וכסא אינו תקין'
            else:
                r = read_from_seat_db(client_id, hall_id, zone_id, row, seat)
                if r is not None:
                    #p(r, r.row, r.seat)
                    error = 'מושב קיים'
                else:
                    error = 'מושב לא נמצא'

        if form.create.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            row = form.row.data
            if row is None: row = ''
            seat = form.seat.data
            if seat is None: seat = ''
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1 or val(row) < 1 or val(seat) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור או מספר שורה וכסא אינו תקין'
            else:
                row_ = seatDB(client_id=client_id, hall_id=hall_id, zone_id=zone_id, row=row, seat=seat, status=False)
                try:
                    db.session.add(row_)
                    db.session.commit()
                    error = 'מושב חדש הוסף בהצלחה'
                except Exception as err:
                    p(err)
                    error = 'שגיאה בהוספת מושב -ייתכן שכבר קיים או שקוד אולם או קוד אזור אינו תקין'
                    pass


        if form.delete.data:
            client_id = form.client_id.data
            if client_id is None: client_id = ''
            hall_id = form.hall_id.data
            if hall_id is None: hall_id = ''
            zone_id = form.zone_id.data
            if zone_id is None: zone_id = ''
            row = form.row.data
            if row is None: row = ''
            seat = form.seat.data
            if seat is None: seat = ''
            row_ = read_from_seat_db(client_id, hall_id, zone_id, row, seat)
            if row_ is None:
                error = 'מושב לא נמצא - לא ניתן למחיקה'
            else:
                db.session.delete(row_)
                db.session.commit()
                if row_ is None:
                    error = 'תקלה במחיקת מושב'
                else:
                    error = 'מושב נמחק'

    return render_template('cartisan_seat.html', title='אולמות',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), row=row, seat=seat, zone_id=zone_id, hall_id=hall_id
        )

def read_from_seat_db(client_id, hall_id, zone_id, row, seat):
    if row is None: # list by client_id, hall_id, zone_id
        result = seatDB.query.filter_by(client_id=client_id, hall_id=hall_id, zone_id=zone_id).all()
        #p(result)
        if result is not None:
            seat_list = []
            for r in result:
                #p(f'data={r.hall_id}, {r.client_id}, {r.zone_id}, {r.row}, {r.seat}')
                seat_list.append([r.row, r.seat])
            #p('OK')
            df_chat = pd.DataFrame(seat_list, columns=['id$', 'name$'])
            #p(df_chat)
            return(df_chat)
    else:
        result = seatDB.query.filter_by(client_id=client_id, hall_id=hall_id, zone_id=zone_id, row=row, seat=seat).first()
    return result

