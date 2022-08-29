from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, StringField, BooleanField
from wtforms.validators import DataRequired, Length#, FileRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired

class MainMenuForm(FlaskForm):
    load = SubmitField('Upload External')
    solve = SubmitField('Run Internal')
    create = SubmitField('Create a Puzzle')

class SolveForm(FlaskForm):
    hashi_num = IntegerField('Hashi Number', validators=[DataRequired(),
        Length(min=2, max=2, message='must be between %(min)d and %(max)d chars')])
    solve = SubmitField('Solve Hashi')
    home = SubmitField('Home')

class CreateForm(FlaskForm):
    nrows = IntegerField('Number of rows (2-20)', validators=[DataRequired()])
    ncols = IntegerField('Number of rows (2-20)', validators=[DataRequired()])
    create = SubmitField('Create Table')
    home = SubmitField('Home')

class LoadForm(FlaskForm):
    file_name = FileField('CSV file name to load', render_kw={'title':''},
            validators=[FileRequired(), FileAllowed(['csv'])])
    load = SubmitField('Load File', render_kw={"onclick": "myFunction()"})
    home = SubmitField('Home')

class ChatForm(FlaskForm):
    user_msg = StringField('User Input', render_kw={'autofocus': True})
    run_bot = SubmitField('Ask Bot')
    google = SubmitField('G')
    debug = SubmitField('Debug')
    run_test = SubmitField('Run Test')
    send_log = SubmitField('Send Log')

class CartisanForm(FlaskForm):
    hall = SubmitField('אולמות')
    zone = SubmitField('אזורים')
    seat = SubmitField('מושבים')

class Cartisan_hallForm(FlaskForm):
    client_id = IntegerField('קוד לקוח (1 עד 20)',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    hall_id = IntegerField('קוד אולם',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    name = StringField('שם אולם',
        render_kw={'dir': "rtl"})
    picture = StringField('קובץ תמונה',
        render_kw={'dir': "rtl"})
    directions = StringField('הוראות הגעה',
        render_kw={'dir': "rtl"})

    hall_list = SubmitField('רשימת אולמות ללקוח')
    search = SubmitField('חפש אולם')
    create = SubmitField('הוסף אולם')
    update = SubmitField('שמור אולם')
    delete = SubmitField('מחק אולם')
    load = SubmitField('העלה קובץ תמונה')
    home = SubmitField('חזרה')

class Cartisan_LoadForm(FlaskForm):
    file_name = FileField('בחר קובץ תמונה עם אחת הסיומות png, jpg, jpeg, gif', render_kw={'title':''},
            validators=[FileRequired(), FileAllowed(['png', 'jpg', 'jpeg', 'gif'])])
    load = SubmitField('העלה קובץ')
#            , render_kw={"onclick": "myFunction()"})
    home = SubmitField('חזרה')

class Cartisan_zoneForm(FlaskForm):
    client_id = IntegerField('קוד לקוח (1 עד 20)',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    hall_id = IntegerField('קוד אולם',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    zone_id = IntegerField('קוד אזור',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    name = StringField('שם אזור',
        render_kw={'dir': "rtl"})
    marked_seats = BooleanField('מקוומות מסומנים',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    max_seats = IntegerField('תכולה',
        render_kw={'dir': "rtl"})

    zone_list = SubmitField('רשימת אזורים באולם')
    search = SubmitField('חפש אזור')
    create = SubmitField('הוסף אזור')
    update = SubmitField('שמור אזור')
    delete = SubmitField('מחק אזור')
    home = SubmitField('חזרה')

class Cartisan_seatForm(FlaskForm):
    client_id = IntegerField('קוד לקוח (1 עד 20)',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    hall_id = IntegerField('קוד אולם',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    zone_id = IntegerField('קוד אזור',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    status = BooleanField('תפוס',
        validators=[DataRequired()], render_kw={'dir': "rtl"})
    row = IntegerField('שורה',
        render_kw={'dir': "rtl"})
    seat = IntegerField('כסא',
        render_kw={'dir': "rtl"})

    seat_list = SubmitField('רשימת מושבים באזור')
    search = SubmitField('חפש מושב')
    create = SubmitField('הוסף מושב')
    delete = SubmitField('מחק מושב')
    home = SubmitField('חזרה')
