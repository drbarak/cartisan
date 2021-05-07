from flask_wtf import FlaskForm
from wtforms import SubmitField, DecimalField#, StringField
from wtforms.validators import DataRequired#, FileRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired

class MainMenuForm(FlaskForm):
    load = SubmitField('Upload External')
    solve = SubmitField('Run Internal')
    create = SubmitField('Create a New')

class GetHashiNumberForm(FlaskForm):
    hashi_num = DecimalField('Hashi Number (2-32)', validators=[DataRequired()])
    solve = SubmitField('Solve Hashi')
    home = SubmitField('Home')

class CreateForm(FlaskForm):
    nrows = DecimalField('Number of row/cols (2-20)', validators=[DataRequired()])
    create = SubmitField('Create Table')
    home = SubmitField('Home')

class LoadForm(FlaskForm):
    file_name = FileField('CSV file name to load', validators=[FileRequired(), FileAllowed(['csv'])])
    load = SubmitField('Load File')
    home = SubmitField('Home')
