# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request
from flask_app import session, app, cleanup
#from sqlalchemy import func
import os #תsys
import pandas as pd
import time
#import numpy as np

from prog.forms import CartisanForm, Cartisan_hallForm, Cartisan_LoadForm, Cartisan_zoneForm, Cartisan_seatForm
from globals import Globals

from prog.cartisan_util import val, p, send_email
#from hashi import val
#from prog.chatbot_init import p, send_email

globals = Globals()

def valid_user():
    return 'username_' in session and session['username_'] == 'admin_'

from flask_app import db, hallDB, zoneDB, seatDB, user_loginDB, userDB

'''
if we come here within 1 minute it is assumed that it is due to flak executing main_menu twice, 
still with request.args.get('ip') == None although only upon entry it is not set and all other
redirect has ip=... defined already, so we ignore it so no duplicate email or 2 login records
'''
IDLE_TIME = 60
ip_address = ''

def clear_session():
    global ip_address
    if 'localhost' in request.headers['Host']:
        ip_address = '127.0.0.1'
    else:
        ip_address = request.headers['X-Real-IP']
    
    delta = time.time() - session['time'] if 'time' in session else IDLE_TIME + 1   # do it no more than once an hour for the same user
    if delta > IDLE_TIME or globals.user_id < 1:

        if globals.user_id < 1:    # to do only once per session
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
            session.pop('mylog', '')

            base_dir = os.path.join(app.root_path, 'static')
            file = base_dir + '/mylog.true'
            globals.write_to_log = True if os.path.exists(file) else False

            p(session)

            db.engine.connect()
            user = userDB.query.filter_by(ip_address=ip_address).first()
            if user is not None:
                #p('Found:', user, user.id, user.ip_address, user.name, user.log)
                globals.user_id = user.id
                globals.user_log = user.log
            else:
                p('ip not found in user file', ip_address)
                try:
                    user = userDB(ip_address=ip_address)
                    db.session.add(user)
                    db.session.commit()
                    if user.id is None:
                        p('error adding user')
                    else:
                        p('New user id=', user.id, 'ip=', user.ip_address, 'log=', user.log)
                        globals.user_id = user.id
                        globals.user_log = user.log
                except Exception as err:
                    p(err)
                    pass
            cleanup(db.session)

        if globals.user_id > 0 and globals.user_log:
            db.engine.connect()
            login_row = user_loginDB(user_id=globals.user_id)
            try:
                db.session.add(login_row)
                db.session.commit()
                if login_row.id is None:
                    p('error adding user_login')
                else:
                    p('New login id=', login_row.id)
            except Exception as err:
                p(err)
                pass
            cleanup(db.session)

            if send_email(text='Message from Cartisan',ip = ip_address, src = f'Cartisan userId = {globals.user_id}'):
                p("Successfully sent email")
            else:
                p("Error: unable to send email")
    else:
        p('delta time =', round(delta, 0) , globals.user_id, ip_address)
        return False
    return True

def url_params(form):
    return '?' +\
        '&ip=' + ip_address +\
        '&hall_id=' + form.hidden_hall_id.data +\
        '&client_id=' + form.hidden_client_id.data +\
        '&zone_id=' + form.hidden_zone_id.data

def main_menu():
    # when starting the app first time the url has no ip, so we know to init the app
    if request.args.get('ip') == None:
        if clear_session():
            p('------------------------------')
            p('Start Cartisan')
            session['time'] = time.time()
    session['picture'] = ''
    client_id = request.args.get('client_id')
    if client_id is None: client_id = ''
    hall_id = request.args.get('hall_id')
    if hall_id is None: hall_id = ''
    zone_id = request.args.get('zone_id')
    if zone_id is None: zone_id = ''

    form = CartisanForm()
    if request.method == 'POST':
        if form.hall.data:
            return redirect('/hall'+ url_params(form))
        elif form.zone.data:
            return redirect('/zone'+ url_params(form))
        elif form.seat.data:
            return redirect('/seat'+ url_params(form))

        return redirect('/cartisan'+ url_params(form))
    
    form.hidden_zone_id.data = zone_id
    form.hidden_hall_id.data = hall_id
    form.hidden_client_id.data = client_id
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

def get_hall_fields(form):
    client_id = form.client_id.data
    if client_id is None: client_id = ''
    hall_id = form.hall_id.data
    if hall_id is None: hall_id = ''
    return client_id, hall_id

def hall():
    form = Cartisan_hallForm()
    df_chat_html = df_chat = error = ''
    name = directions = url_icon = ''
    search_row = None
    picture = session['picture']
    
    client_id = request.args.get('client_id')
    if client_id is None: client_id = ''
    hall_id = request.args.get('hall_id')
    if hall_id is None: hall_id = ''
    zone_id = request.args.get('zone_id')
    if zone_id is None: zone_id = ''

    if valid_user() and not (request.method == 'POST' or val(client_id) < 1 or val(client_id) > 20 or val(hall_id) < 1):
        db.engine.connect()
        search_row = read_from_hall_db(client_id, hall_id)
        if search_row is None:
            error = 'אולם לא נמצא'
        cleanup(db.session)
    
    elif valid_user() and request.method == 'POST':
        if form.home.data:
            session['picture'] = ''
            return redirect('/cartisan' + url_params(form))
        elif form.zone.data:
            return redirect('/zone' + url_params(form))
        
        if form.hall_list.data:
            client_id, _ = get_hall_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            else:
                db.engine.connect()
                df = read_from_hall_db(client_id, None)
                cleanup(db.session)
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
            client_id, hall_id = get_hall_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1:
                error = 'קוד לקוח או קוד אולם אינו תקין'
            else:
                db.engine.connect()
                search_row = read_from_hall_db(client_id, hall_id)
                if search_row is None:
                    error = 'אולם לא נמצא'
                cleanup(db.session)

        if form.update.data:
            client_id, hall_id = get_hall_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1:
                error = 'קוד לקוח או קוד אולם אינו תקין'
            else:
                db.engine.connect()
                hall = read_from_hall_db(client_id, hall_id)
                if hall is not None:
                    name = hall.name = form.name.data
                    picture = hall.picture = form.picture.data
                    directions = hall.directions = form.directions.data
                    url_icon = picture_dir + picture if picture != '' else ''
                    db.session.commit()
                    session['picture'] = ''
                cleanup(db.session)
                
        if form.create.data:
            client_id, hall_id = get_hall_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif not(val(hall_id) < 1):
                error = 'קוד אולם חייב להיות ריק - המערכת תעדכן את קוד האולם החדש'
            else:
                hall = hallDB(client_id=client_id, name=form.name.data, picture=form.picture.data, directions=form.directions.data)
                db.engine.connect()
                db.session.add(hall)
                db.session.commit()
                if hall.id is None:
                    error = 'תקלה בהוספת אולם'
                else:
                    hall_id = form.hall_id.data = hall.id
                    error = 'קוד אולם חדש'
                    name = form.name.data
                    picture = form.picture.data
                    directions = form.directions.data
                    url_icon = picture_dir + picture if picture != '' else ''
                    session['picture'] = ''
                cleanup(db.session)

        if form.delete.data:
            client_id, hall_id = get_hall_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'יש לספק קוד לקוח'
            elif val(hall_id) < 1:
                error = 'יש לספק קוד אולם'
            else:
                db.engine.connect()
                hall = read_from_hall_db(client_id, hall_id)
                if hall is None:
                    error = 'אולם לא נמצא - לא ניתן למחיקה'
                else:
                    db.session.delete(hall)
                    db.session.commit()
                    if hall.id is None:
                        error = 'תקלה במחיקת אולם'
                    else:
                        hall_id = ''
                        error = 'אולם נמחק'
                        session['picture'] = ''
                cleanup(db.session)

        if form.load.data:
            client_id, hall_id = get_hall_fields(form)
            picture = form.picture.data
            if picture == '' or picture is None:
                error = 'שם קובץ תמונה לא תקין'
            else:  # make sure a file with than name does not exists
                base_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                file = base_dir + '/' + picture
                #p(file)
                if os.path.exists(file):
                    error = 'קובץ כבר קיים'
                    db.engine.connect()
                    search_row = read_from_hall_db(client_id, hall_id)
                    cleanup(db.session)
                else:
                    session['picture'] = picture
                    return redirect('/cartisan_load' + url_params(form))

    form.hidden_zone_id.data = zone_id
    form.hidden_hall_id.data = hall_id
    form.hidden_client_id.data = client_id
    if search_row is not None:
        hall = search_row
        name = hall.name if hall.name is not None else ''
        picture = hall.picture if hall.picture is not None else ''
        directions = hall.directions if hall.directions is not None else ''
        url_icon = picture_dir + picture if picture != '' else ''
        session['picture'] = ''
        
    return render_template('cartisan_hall.html', title='אולמות',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), name=name, picture=picture, directions=directions, url_icon=url_icon, 
        client_id=client_id, hall_id=hall_id
        )

def read_from_hall_db(client_id, hall_id):
    if hall_id is None: # search by client_id
        result = hallDB.query.filter_by(client_id=client_id).all()
        if result is None or result == []:
            return None
        hall_list = []
        for hall in result:
            hall_list.append([hall.id, hall.name])
        df_chat = pd.DataFrame(hall_list, columns=['id$', 'name$'])
        return(df_chat)
    return hallDB.query.get(hall_id)
    
def load():
    form = Cartisan_LoadForm()
    error = ''
    
    client_id = request.args.get('client_id')
    if client_id is None: client_id = ''
    hall_id = request.args.get('hall_id')
    if hall_id is None: hall_id = ''
    zone_id = request.args.get('zone_id')
    if zone_id is None: zone_id = ''

    if valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/hall' + url_params(form))

        if form.load.data and form.file_name.data:
            if form.validate_on_submit():
                file = form.file_name.data
                if file and allowed_file(file.filename):
                    picture=session['picture']
                    filename = secure_filename(picture)
                    base_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                    p(os.path.join(base_dir, filename))
                    file.save(os.path.join(base_dir, filename))
                    return redirect('/hall' + url_params(form))
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
            
    form.hidden_zone_id.data = zone_id
    form.hidden_hall_id.data = hall_id
    form.hidden_client_id.data = client_id
    return render_template('cartisan_load.html', form=form, error=error)

def list_zones(client_id, hall_id):
    db.engine.connect()
    df = read_from_zone_db(client_id, hall_id, None)
    cleanup(db.session)
    df_chat_html = df_chat = error = ''

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
    return df_chat_html, df_chat, error
    
def get_zone_fields(form):
    client_id = form.client_id.data
    if client_id is None: client_id = ''
    hall_id = form.hall_id.data
    if hall_id is None: hall_id = ''
    zone_id = form.zone_id.data
    if zone_id is None: zone_id = ''
    return client_id, hall_id, zone_id

def zone():
    form = Cartisan_zoneForm()
    df_chat_html = df_chat = error = ''
    name = marked_seats = max_seats = zone_id = ''
    marked_seats = False
    search_row = None

    client_id = request.args.get('client_id')
    if client_id is None: client_id = ''
    hall_id = request.args.get('hall_id')
    if hall_id is None: hall_id = ''
    zone_id = request.args.get('zone_id')
    if zone_id is None: zone_id = ''
    hall_name = ''
 
    if valid_user() and not (request.method == 'POST' or val(client_id) < 1 or val(client_id) > 20 or val(hall_id) < 1):
        if request.args.get('search') is None:
            df_chat_html, df_chat, error = list_zones(client_id, hall_id)
            hall_name = get_hall(hall_id)
        else:
            db.engine.connect()
            search_row = read_from_zone_db(client_id, hall_id, zone_id)
            if search_row is None:
                error = 'אולם לא נמצא'
            cleanup(db.session)

    elif valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/cartisan' + url_params(form))
        if form.hall.data:
            return redirect('/hall' + url_params(form) + '&search')
        elif form.seat.data:
            return redirect('/seat' + url_params(form))
        
        if form.zone_list.data:
            client_id, hall_id, _ = get_zone_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif (val(hall_id) < 1):
                error = 'קןד אולם אינו תקין'
            else:
                df_chat_html, df_chat, error = list_zones(client_id, hall_id)
            if not val(hall_id) < 1:
                hall_name = get_hall(hall_id)

        if form.search.data:
            client_id, hall_id, zone_id = get_zone_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור אינו תקין'
            else:
                db.engine.connect()
                search_row = read_from_zone_db(client_id, hall_id, zone_id)
                cleanup(db.session)
                if search_row is None:
                    error = 'אזור לא נמצא'
            if not val(hall_id) < 1:
                hall_name = get_hall(hall_id)


        if form.update.data:
            client_id, hall_id, zone_id = get_zone_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור אינו תקין'
            else:
                db.engine.connect()               
                r = read_from_zone_db(client_id, hall_id, zone_id)
                if r is not None:
                    name = r.name = form.name.data
                    marked_seats = r.marked_seats = 'marked_seats' in request.form
                    max_seats = r.max_seats = form.max_seats.data if val(form.max_seats.data) > 0 else 0
                    db.session.commit()
                cleanup(db.session)
            if not val(hall_id) < 1:
                hall_name = get_hall(hall_id)

        if form.create.data:
            client_id, hall_id, zone_id = get_zone_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif val(hall_id) < 1:
                error = 'קוד אולם אינו תקין'
            elif (zone_id != ''):
                error = 'קוד אזור חייב להיות ריק - המערכת תעדכן את קוד האזור החדש'
            else:
                max_seats = form.max_seats.data if val(form.max_seats.data) > 0 else 0
                marked_seats = 'marked_seats' in request.form
                row = zoneDB(client_id=client_id, hall_id=hall_id, name=form.name.data, marked_seats=marked_seats, max_seats=max_seats)
                try:
                    db.engine.connect() 
                    db.session.add(row)
                    db.session.commit()
                    if row.id is None:
                        error = 'תקלה בהוספת אזור'
                    else:
                        zone_id = form.zone_id.data = row.id
                        error = 'קוד אזור חדש'
                        name = form.name.data
                    cleanup(db.session)
                except Exception as err:
                    p(err)
                    error = 'שגיאה בהוספת אזור - יתכן שקוד האולם אינו קיים'
                    pass
            if not val(hall_id) < 1:
                hall_name = get_hall(hall_id)

        if form.delete.data:
            client_id, hall_id, zone_id = get_zone_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'יש לספק קוד לקוח'
            elif (val(hall_id) < 1):
                error = 'יש לספק קוד אולם'            
            elif (val(zone_id) < 1):
                error = 'יש לספק קוד אזור'
            else:
                db.engine.connect() 
                row = read_from_zone_db(client_id, hall_id, zone_id)
                if row is None or row.id is None:
                    error = 'אזור לא נמצא - לא ניתן למחיקה'
                else:
                    db.session.delete(row)
                    db.session.commit()
                    if row.id is None:
                        error = 'תקלה במחיקת אזור'
                    else:
                        error = 'אזור נמחק'
                        zone_id = ''
                cleanup(db.session)
            if not val(hall_id) < 1:
                hall_name = get_hall(hall_id)

    form.hidden_zone_id.data = zone_id
    form.hidden_hall_id.data = hall_id
    form.hidden_client_id.data = client_id
    if search_row is not None:
        r = search_row
        name = r.name if r.name is not None else ''
        marked_seats = r.marked_seats if r.marked_seats is not None else ''
        max_seats = r.max_seats if r.max_seats is not None else ''
        hall_name = get_hall(hall_id)

    return render_template('cartisan_zone.html', title='אזורים',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), name=name, marked_seats=marked_seats, zone_id=zone_id,
            hall_id=hall_id, client_id=client_id, hall_name=hall_name,
            max_seats=max_seats if val(max_seats) > 0 else ''
        )

def read_from_zone_db(client_id, hall_id, zone_id):
    if zone_id is None: # search by client_id and hall_id
        result = zoneDB.query.filter_by(client_id=client_id, hall_id=hall_id).all()
        if result is None or result == []:
            return None
        zone_list = []
        for r in result:
            #p(f'data={r.id}, {r.client_id}, {r.name}, {r.picture}, {r.directions}')
            zone_list.append([r.id, r.name])
        #p('OK')
        df_chat = pd.DataFrame(zone_list, columns=['id$', 'name$'])
        #p(df_chat)
        return(df_chat)
    return zoneDB.query.get(zone_id)

def get_hall(hall_id):
    hall_name = ''
    db.engine.connect()
    hall = hallDB.query.get(hall_id)
    if hall is not None:
        hall_name = hall.name
    cleanup(db.session)
    return hall_name
    
def get_seat_fields(form):
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
    return client_id, hall_id, zone_id, row, seat

def list_seats(client_id, hall_id, zone_id):
    db.engine.connect()
    df = read_from_seat_db(client_id, hall_id, zone_id, None, None)
    cleanup(db.session)
    df_chat_html = df_chat = error = ''

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
    return df_chat_html, df_chat, error

def seat():
    form = Cartisan_seatForm()
    df_chat_html = df_chat = error = ''
    hall_id = row = seat = zone_id = ''
    hall_name = zone_name = ''
    marked_seats = False

    client_id = request.args.get('client_id')
    if client_id is None: client_id = ''
    hall_id = request.args.get('hall_id')
    if hall_id is None: hall_id = ''
    zone_id = request.args.get('zone_id')
    if zone_id is None: zone_id = ''

    if valid_user() and not (request.method == 'POST' or val(client_id) < 1 or val(client_id) > 20 
                        or val(hall_id) < 1 or val(zone_id) < 1):
        df_chat_html, df_chat, error = list_seats(client_id, hall_id, zone_id)
        hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)

    elif valid_user() and request.method == 'POST':
        if form.home.data:
            return redirect('/cartisan' + url_params(form))
        if form.hall.data:
            return redirect('/hall' + url_params(form) + '&search')
        elif form.zone.data:
            return redirect('/zone' + url_params(form) + '&search')
        
        if form.seat_list.data:
            client_id, hall_id, zone_id, _, _ = get_seat_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20):
                error = 'קןד לקוח אינו תקין'
            elif (val(hall_id) < 1):
                error = 'קןד אולם אינו תקין'
            elif (val(zone_id) < 1):
                error = 'קןד אזור אינו תקין'
            else:
                df_chat_html, df_chat, error = list_seats(client_id, hall_id, zone_id)
                hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)

        if form.search.data:
            client_id, hall_id, zone_id, row, seat = get_seat_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1 or val(row) < 1 or val(seat) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור או מספר שורה וכסא אינו תקין'
            else:
                db.engine.connect()
                seat_row = read_from_seat_db(client_id, hall_id, zone_id, row, seat)
                if seat_row is not None:
                    error = 'מושב נמצא'
                else:
                    error = 'מושב לא נמצא'
                cleanup(db.session)
            if not ((val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1):
                hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)

        if form.create.data:
            client_id, hall_id, zone_id, row, seat = get_seat_fields(form)
            if (val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1 or val(row) < 1 or val(seat) < 1:
                error = 'קוד לקוח או קוד אולם או קוד אזור או מספר שורה וכסא אינו תקין'
            else:
                hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)
                if not marked_seats:
                    error = 'לא ניתן להוסיף מושב באזור ללא מקומות מסומנים'
                else:
                    r = seatDB(client_id=client_id, hall_id=hall_id, zone_id=zone_id, row=row, seat=seat, status=False)
                    try:
                        db.engine.connect()
                        db.session.add(r)
                        db.session.commit()
                        cleanup(db.session)
                        error = 'מושב חדש הוסף בהצלחה'
                    except Exception as err:
                        p(err)
                        error = 'שגיאה בהוספת מושב -ייתכן שכבר קיים או שקוד אולם או קוד אזור אינו תקין'
                        pass
            if not ((val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1):
                hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)

        if form.delete.data:
            client_id, hall_id, zone_id, row, seat = get_seat_fields(form)
            db.engine.connect()
            r = read_from_seat_db(client_id, hall_id, zone_id, row, seat)
            if r is None:
                error = 'מושב לא נמצא או שחסר נתון לחיפוש - לא ניתן למחיקה'
            else:
                db.session.delete(r)
                db.session.commit()
                if r is None:
                    error = 'תקלה במחיקת מושב'
                else:
                    error = 'מושב נמחק'
                    row = seat = ''
            cleanup(db.session)
            if not ((val(client_id) < 1 or val(client_id) > 20) or val(hall_id) < 1 or val(zone_id) < 1):
                hall_name, zone_name, marked_seats = get_hall_zone_names(client_id, hall_id, zone_id)

    form.hidden_zone_id.data = zone_id
    form.hidden_hall_id.data = hall_id
    form.hidden_client_id.data = client_id
    return render_template('cartisan_seat.html', title='מושבים',
        form=form, error=error,
        df_chat=df_chat_html, length=len(df_chat), zone_id=zone_id, hall_id=hall_id, client_id=client_id,
            row=row if val(row) > 0 else '', seat=seat if val(seat) > 0 else '',
            hall_name=hall_name, zone_name=zone_name
        )

def read_from_seat_db(client_id, hall_id, zone_id, row, seat):
    if row is None: # list by client_id, hall_id, zone_id
        result = seatDB.query.filter_by(client_id=client_id, hall_id=hall_id, zone_id=zone_id).all()
        if result is not None:
            seat_list = []
            for seat_row in result:
                seat_list.append([seat_row.row, seat_row.seat])
            df_chat = pd.DataFrame(seat_list, columns=['id$', 'name$'])
            return(df_chat)
    else:
        result = seatDB.query.filter_by(client_id=client_id, hall_id=hall_id, zone_id=zone_id, row=row, seat=seat).first()
    return result

def get_hall_zone_names(client_id, hall_id, zone_id):
    hall_name = zone_name = ''
    marked_seats = False
    db.engine.connect()
    hall = hallDB.query.get(hall_id)
    if hall is not None:
        hall_name = hall.name
        zone = read_from_zone_db(client_id, hall_id, zone_id)
        if zone is not None:
            zone_name = zone.name
            marked_seats = zone.marked_seats
    cleanup(db.session)
    return hall_name, zone_name, marked_seats
