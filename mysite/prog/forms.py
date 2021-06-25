from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, StringField
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
