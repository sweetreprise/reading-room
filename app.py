import os

from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
import requests

from models import db, connect_db, User
from forms import LoginForm, RegisterForm

# CURR_USER_KEY = "current_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///reading_room'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

bcrypt = Bcrypt()

connect_db(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    """Homepage."""
    if not current_user.is_authenticated:
        app.login_manager.unauthorized()
        form = LoginForm()
        return render_template('/users/login.html', form=form)
    else:
        return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers a user. If the username is already taken, an error is raised."""
    form = RegisterForm()

    if form.validate_on_submit():
        try:
            new_user = User.register(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=form.password.data
            )
            db.session.commit()
        except IntegrityError:
            flash("The username is already taken. Please choose another.", 'danger')
            return render_template('/users/register.html', form=form)

    return render_template('users/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user, authenticates the submitted username and password."""
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data
        )
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))

        flash("The username/password you entered in incorrect. Please try again.", 'danger')

    return render_template('users/login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logs out user."""
    logout_user()
    return redirect('login')

@app.route('/dashboard')
@login_required
def dashboard():
    """Displays dashboard."""
    
    return render_template('users/dashboard.html')

@app.route('/search', methods=['POST'])
def search():
    """Searches for books."""

    search = request.form['search']
    response = requests.get("http://openlibrary.org/search.json",
        params={'q': search, 'limit': 50})
    json_obj = response.json()
    results = json_obj['docs']
    return render_template('search.html', results=results)








