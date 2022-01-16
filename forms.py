"""Forms for Reading Room"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Length
from models import User

class RegisterForm(FlaskForm):
    """Form to register a user"""

    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First name', validators=[DataRequired()])
    last_name = StringField('Last name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=8, max=20)])

    # @classmethod
    # def validate_username(self, username):
    #     existing_username = User.query.filter_by(username=username.data).first()

    #     if existing_username:
    #         raise ValidationError(
    #             "That username already exists. Please choose a different one"
            # )

class LoginForm(FlaskForm):
    """Form to login a user"""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=8)])

class UserEditForm(FlaskForm):
    """Form for a user to edit their details"""

    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First name', validators=[DataRequired()])
    last_name = StringField('Last name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=8, max=20)])
    description = TextAreaField('Description')
    image_url = TextAreaField('User photo')

# class AddBookToShelfForm(FlaskForm):
#     """Form for adding a book to a user's shelf"""


