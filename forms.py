"""Forms for Reading Room"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, ValidationError, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from models import User

class RegisterForm(FlaskForm):
    """Form to register a user"""

    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First name', validators=[DataRequired()])
    last_name = StringField('Last name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=20)])

class LoginForm(FlaskForm):
    """Form to login a user"""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=8)])

class UserEditForm(FlaskForm):
    """Form for a user to edit their details"""

    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First name', validators=[DataRequired()])
    last_name = StringField('Last name', validators=[DataRequired()])
    description = TextAreaField('Description')
    image_url = TextAreaField('User photo')
    password = PasswordField('Password', validators=[Length(min=8, max=20)])

class AddBookToShelfForm(FlaskForm):
    """Form for adding a book to a user's shelf"""

    status = SelectField('', choices=[('reading', 'Reading'), ('finished-reading', 'Finished Reading'), ('future-reads', 'Future Reads')])

class EditBookForm(FlaskForm):
    """Form for a user to edit a book on their shelf"""

    status = SelectField('Status', choices=[('reading', 'Reading'), ('finished-reading', 'Finished Reading'), ('future-reads', 'Future Reads')])
    num_pages = IntegerField('Number of pages', default=0, validators=[Optional(), NumberRange(min=0)])
    pages_read = IntegerField('Pages Read', default=0, validators=[Optional(), NumberRange(min=0)])


    


