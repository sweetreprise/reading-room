import os

from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
import requests
import itertools

from models import DEFAULT_COVER_IMG, db, connect_db, User, Shelf, Book
from forms import LoginForm, RegisterForm, UserEditForm, AddBookToShelfForm, EditBookForm

# CURR_USER_KEY = "current_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('HEROKU_POSTGRESQL_AQUA_URL','postgresql:///reading_room').replace('postgres://', 'postgresql://', 1)



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
    # if not current_user.is_authenticated:
    #     app.login_manager.unauthorized()
    #     form = LoginForm()
    #     return render_template('/users/login.html', form=form)
    # else:
    #     return render_template('home.html')

    if current_user.is_authenticated:
        return redirect('/dashboard')
    else:
        return render_template('home.html')

@app.route('/faq')
def faq():
    """Displays FAQ"""

    return render_template('/faq.html')

###################### REGISTER, LOGIN, LOGOUT ########################

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

        login_user(new_user)
        return redirect('/dashboard')

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
    return redirect('/')


###################### SEARCH ROUTE ########################

@app.route('/search', methods=['POST'])
def search():
    """Searches for books."""

    search = request.form['search']
    response = requests.get("http://openlibrary.org/search.json",
        params={'q': search, 'limit': 50})
    json_obj = response.json()
    results = json_obj['docs']
    return render_template('search.html', results=results)


@app.route('/works/<string:key>', methods=['GET'])
def get_book_info(key):
    """Displays info about a specific book: cover, description, editions, author"""

    response = requests.get(f"https://openlibrary.org/works/{ key }.json")
    json_obj = response.json()

    authors = get_author(json_obj)
    form = AddBookToShelfForm()

    return render_template('books/info.html', json=json_obj, authors=authors, form=form, key=key)

@app.route('/works/<string:key>', methods=['POST'])
@login_required
def add_book_to_shelf(key):
    """Adds book to a user's shelf"""

    user = User.query.get_or_404(current_user.id)
    status = request.form['status']
    progress = Shelf.check_progress(status)

    #if book object does not already exist, create book object
    if not Book.check_book(key):
        create_book_obj(key)

    entry = Shelf.check_existing(user.id, key)

    #checks if book is already part of a user's shelf
    ## if it is, changes the status based on the form
    ### if not, creates new entry and adds to shelf
    if entry:
            entry.status=status
            entry.progress=progress
    else:
        entry = Shelf(
            user_id=user.id,
            book_key=key,
            status=status,
            progress=progress
        )
    db.session.add(entry)
    db.session.commit()

    flash('Successfully added to your shelf!', 'success')

    return redirect(f'/works/{key}')

# helper function
def create_book_obj(key):
    """Creates a book object and commits to database"""

    response = requests.get(f"https://openlibrary.org/works/{ key }.json")
    json = response.json()

    title = json['title']
    author_names = get_author(json)
    author_string = ', '.join([str(author) for author in author_names])
    
    desc = check_valid_desc(json)

    if json['covers']:
        cover = json['covers'][0]
    else:
        cover = DEFAULT_COVER_IMG

    new_book = Book(
        key=key,
        title=title,
        author_name=author_string,
        description=desc,
        cover=cover
    )

    db.session.add(new_book)
    db.session.commit()

# helper function
def check_valid_desc(json):
    """parses out a book's description based on the format recieved in the request"""
    if 'description' not in json.keys():
        desc = "No description available"
    elif type(json['description']) == str:
        desc = json['description']
    else:
        desc = json['description']['value']

    return desc


# helper function
def get_author(json_obj):
    """Gets author name from author key derived from a piece of work"""
    author_key = []
    authors = []

    for author in json_obj['authors']:
        author_key.append(author['author']['key'])
    
    for key in author_key:
        response = requests.get(f'https://openlibrary.org/{ key }.json')
        json = response.json()
        authors.append(json['name'])
    
    return authors


###################### USER ROUTES ########################

@app.route('/dashboard')
@login_required
def dashboard():
    """Displays dashboard."""

    user = User.query.get_or_404(current_user.id)
    shelves = user.shelves

    # shelves = Shelf.query.filter_by(user_id=user.id).order_by("title")

    books_array = get_books_array(shelves)
    reading = books_array[0]
    finished_reading = books_array[1]
    future_reads = books_array[2]

    return render_template('users/dashboard.html', user=user, reading=reading, finished_reading=finished_reading, future_reads=future_reads)

#helper function
def get_books_array(shelves):
    """Returns an array of arrays. Each nested array is sorted from their status"""
    reading = []
    finished_reading = []
    future_reads = []

    for book in shelves:
        if book.status == 'reading':
            reading.append(book)
        elif book.status == 'finished-reading':
            finished_reading.append(book)
        else:
            future_reads.append(book)

    return [reading, finished_reading, future_reads]

@app.route('/<string:username>')
@login_required
def profile(username):
    """Show's user's info."""

    return render_template('users/profile.html')

@app.route('/<string:username>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(username):
    """Edit user details"""

    user = User.query.get_or_404(current_user.id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        if User.check_unique_username(user, form.username.data):
            form.username.errors = ["This username is already taken"]
        
        elif User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.image_url = form.image_url.data
            user.description = form.description.data
            db.session.commit()

            return redirect(f'/{user.username}')
        else:
            form.password.errors = ['You have entered an invalid password']

    return render_template('users/edit-user.html', form=form)


###################### SHELF ROUTES ########################

@app.route('/<string:username>/shelves')
@login_required
def shelves(username):
    """shows user's shelves"""

    user = User.query.get_or_404(current_user.id)
    shelves = user.shelves

    books_array = get_books_array(shelves)
    reading = books_array[0]
    finished_reading = books_array[1]
    future_reads = books_array[2]

    return render_template('users/shelves.html', user=user, reading=reading, finished_reading=finished_reading, future_reads=future_reads)

@app.route('/<string:username>/shelves/<string:book_key>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(username, book_key):
    """Edits a book on a user's shelf"""

    user = User.query.get_or_404(current_user.id)
    form = EditBookForm()

    return render_template('books/edit-book.html', form=form, user=user)

@app.route('/<string:username>/shelves/<string:book_key>/delete', methods=['GET', 'POST'])
@login_required
def delete_book(username, book_key):
    """Deletes a book from a user's shelf"""

    return render_template('books/delete-book.html')
















