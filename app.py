import os

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
import requests

from models import DEFAULT_COVER_IMG, db, connect_db, User, Shelf, Book, Request
from forms import LoginForm, RegisterForm, UserEditForm, EditBookForm, AddBookToShelfForm


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

@app.route('/dashboard')
@login_required
def dashboard():
    """Displays dashboard."""

    user = User.query.get_or_404(current_user.id)
    shelves = user.shelves

    books_array = get_books_array(shelves)
    reading = books_array[0]
    finished_reading = books_array[1]
    future_reads = books_array[2]

    return render_template('users/dashboard.html', user=user, reading=reading, finished_reading=finished_reading, future_reads=future_reads)

@app.route('/faq')
def faq():
    """Displays FAQ"""

    return render_template('/faq.html')


###################### REGISTER, LOGIN, LOGOUT ########################

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers a user. If the username is already taken, an error is raised."""

    if current_user.is_authenticated:
        return redirect('/')

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


###################### BOOK ROUTE ########################

@app.route('/works/<string:key>', methods=['GET'])
@login_required
def get_book_info(key):
    """Displays info about a specific book: cover, description, author"""

    response = requests.get(f"https://openlibrary.org/works/{ key }.json")
    json_obj = response.json()

    authors = get_author(json_obj)
    form = EditBookForm()

    return render_template('books/info.html', json=json_obj, authors=authors, form=form, key=key)


@app.route('/works/<string:key>', methods=['POST'])
@login_required
def add_book_to_shelf(key):
    """Adds book to a user's shelf"""

    user = User.query.get_or_404(current_user.id)
    status = request.form['status']
    num_pages = int(request.form['num_pages'])
    pages_read = int(request.form['pages_read'])

    if int(pages_read) > int(num_pages):
        flash('Sorry the number of pages read cannot exceed the total number of pages in your book!', 'danger')
        return redirect(request.referrer)

    progress = Shelf.calculate_progress(status, num_pages, pages_read)

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
            entry.num_pages=num_pages
            entry.pages_read=pages_read
    else:
        entry = Shelf(
            user_id=user.id,
            book_key=key,
            status=status,
            num_pages=num_pages,
            pages_read=pages_read,
            progress=progress
        )
    db.session.add(entry)
    db.session.commit()

    flash('Successfully added to your shelf!', 'success')

    return redirect(f'/works/{key}')


###################### USER ROUTES ########################


@app.route('/<string:username>')
@login_required
def profile(username):
    """Show's user's info."""

    curr_user = User.query.get_or_404(current_user.id)
    other_user = User.query.filter_by(username=username).first()

    if other_user:
        return render_template('users/profile.html', curr_user=curr_user, other_user=other_user)
    else:
        flash('Oops! That is not a valid url.', 'danger')
        return redirect('/dashboard')


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

@app.route('/shelves/<string:username>')
@login_required
def shelves(username):
    """shows user's shelves.
    Redirects to a user's currently reading list."""

    return redirect(f'/shelves/{username}/0')


@app.route('/shelves/<string:username>/0')
@login_required
def reading(username):
    """Shows books a user is currently reading."""

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Oops!. this is an invalid url.', 'danger')
        return redirect('/dashboard')
    
    shelves = Shelf.query.filter_by(user_id=user.id).join(Shelf.book).order_by(Book.title)

    books_array = get_books_array(shelves)
    reading = books_array[0]

    if not reading:
        empty = True
    else:
        empty = False
    
    if user.id == current_user.id: 
        return render_template('users/shelves.html', user=user, reading=reading, empty=empty)
    else:
        return render_template('users/friend-shelves.html', user=user, reading=reading, empty=empty)


@app.route('/shelves/<string:username>/1')
@login_required
def finished(username):
    """Shows books a user is finished reading."""

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Oops!. this is an invalid url.', 'danger')
        return redirect('/dashboard')

    shelves = Shelf.query.filter_by(user_id=user.id).join(Shelf.book).order_by(Book.title)

    books_array = get_books_array(shelves)
    finished_reading = books_array[1]

    if not finished_reading:
        empty = True
    else:
        empty = False

    if user.id == current_user.id: 
        return render_template('users/shelves.html', user=user, finished_reading=finished_reading, empty=empty)
    else:
        return render_template('users/friend-shelves.html', user=user, finished_reading=finished_reading, empty=empty)


@app.route('/shelves/<string:username>/2')
@login_required
def future(username):
    """Shows books a user wants to read."""

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Oops!. this is an invalid url.', 'danger')
        return redirect('/dashboard')

    shelves = Shelf.query.filter_by(user_id=user.id).join(Shelf.book).order_by(Book.title)

    books_array = get_books_array(shelves)
    future_reads = books_array[2]

    if not future_reads:
        empty = True
    else:
        empty = False

    if user.id == current_user.id: 
        return render_template('users/shelves.html', user=user, future_reads=future_reads, empty=empty)
    else:
        return render_template('users/friend-shelves.html', user=user, future_reads=future_reads, empty=empty)


@app.route('/shelves/<string:book_key>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_key):
    """Edits a book on a user's shelf"""

    user = User.query.get_or_404(current_user.id)
    book = Shelf.query.filter_by(
        book_key=book_key,
        user_id=user.id
    ).first()

    if not book:
        flash('Oops! That is not a valid url.', 'danger')
        return redirect(request.referrer)

    form = EditBookForm(obj=book)
    status = form.status.data
    num_pages = form.num_pages.data
    pages_read = form.pages_read.data
    progress = Shelf.calculate_progress(status, num_pages, pages_read)

    if form.validate_on_submit():
        book.status = status
        book.num_pages = num_pages
        book.pages_read = pages_read
        book.progress = progress
        db.session.commit()
        flash('Successfully edited!', 'success')
        return redirect(f'/shelves/{user.username}')
    
    return render_template('books/edit-book.html', form=form, user=user, book=book)


@app.route('/shelves/<string:book_key>/delete', methods=['GET', 'POST'])
@login_required
def delete_book(book_key):
    """Deletes a book from a user's shelf"""

    user = User.query.get_or_404(current_user.id)
    book = Shelf.query.filter_by(
        book_key=book_key,
        user_id=user.id
    ).first()

    if not book:
        flash('Oops! That is not a valid url.', 'danger')
        return redirect(request.referrer)
    if request.method == 'POST':
        db.session.delete(book)
        db.session.commit()
        flash('Book deleted!', 'success')
        return redirect(f'/shelves/{user.username}')
    else:
        return render_template('books/delete-book.html', book=book)


###################### FRIEND ROUTES ########################

@app.route('/friends')
@login_required
def friends():
    """Shows a user's friends and their requests."""

    user = User.query.get_or_404(current_user.id)
    received, sent = get_friend_requests(user.id)
    friends = get_friends(user.id)
    f1 = friends[0]
    f2 = friends[1]

    return render_template('/users/friends.html', user=user, received=received, sent=sent, friends=friends, f1=f1, f2=f2)


@app.route('/friends/search', methods=['GET'])
@login_required
def search_user():
    """Search for a user by username and return results."""

    user_input = request.args.get("q")

    search_results = User.query.filter_by(username=user_input).all()

    return render_template('/users/friends-search.html', search_results=search_results, input=user_input)


@app.route('/add-friend', methods=['POST'])
@login_required
def add_friend():
    """Sends a friend request to another user."""

    user_a_id = current_user.id
    user_b_id = int(request.form.get('user_b_id'))

    if user_a_id == user_b_id:
        flash('Oops! You cannot add yourself a friend.', 'danger')
        return redirect(request.referrer)

    status = check_request_status(user_a_id, user_b_id)

    if status == "Friends":
        flash('You two are already friends!', 'primary')
        return redirect(request.referrer)
    elif status == "Pending":
        flash('Your friend request is pending.', 'warning')
        return redirect(request.referrer)
    else:
        friend_request = Request(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            status="Pending"
        )

        db.session.add(friend_request)
        db.session.commit()

        flash('Request Sent!', 'success')

    return redirect('/friends')

@app.route('/friends/accept/<int:user_id>', methods=['POST'])
@login_required
def accept_request(user_id):
    """Accepts friend request."""

    friend_request = Request.query.filter_by(
        user_a_id=user_id,
        user_b_id=current_user.id,
        status="Pending"
    ).first()

    friend_request.status="Friends"
    db.session.commit()
    flash('You have accepted the friend request!', 'success')

    return redirect('/friends')

@app.route('/friends/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_request(user_id):
    """Deletes a user's friend request."""

    friend_request = Request.query.filter_by(
        user_a_id=current_user.id,
        user_b_id=user_id,
        status="Pending"
    ).first()

    db.session.delete(friend_request)
    db.session.commit()
    flash('Your friend request has been deleted.', 'success')

    return redirect('/friends')
    

#helper function
def check_request_status(user_a_id, user_b_id):
    """Checks the friend status between two users. Returns the status."""
    request = Request.query.filter_by(user_a_id=user_a_id, user_b_id=user_b_id).first()
    request2 = Request.query.filter_by(user_a_id=user_b_id, user_b_id=user_a_id).first()

    if request:
        friend_status = request.status
    elif request2:
        friend_status = request2.status
    else:
        friend_status = False

    return friend_status

#helper function
def get_friend_requests(user_id):
    """Gets user's friend requests."""

    received = Request.query.filter_by(
        user_b_id=user_id,
        status='Pending'
        ).all()

    sent = Request.query.filter_by(
        user_a_id=user_id,
        status='Pending'
        ).all()
    
    return received, sent

#helper function
def get_friends(user_id):
    """Returns a users friends.
    This returns a list of lists of friends.
    The query objects are separated depending on whichever column name
    (user_a_id or user_b_id) contains the current user's id.
    This is in order to easily access a user's details when displaying friends."""

    f1 = Request.query.filter_by(
        user_a_id=user_id,
        status="Friends"
    ).all()

    f2 = Request.query.filter_by(
        user_b_id=user_id,
        status="Friends"
    ).all()

    return [f1, f2]


###################### SEARCH ROUTES ########################

@app.route('/search', methods=['GET'])
@login_required
def show_search():
    """Displays search page"""

    return render_template('search.html')

@app.route('/search', methods=['POST'])
@login_required
def search():
    """Searches for books."""

    search = request.form['search']
    response = requests.get("http://openlibrary.org/search.json",
        params={'q': search, 'limit': 50})
    json_obj = response.json()
    
    if json_obj['numFound'] == 0:
        flash('Sorry! Your search yielded no results. Please try again.', 'danger')
        return redirect('/search')
    else:
        results = json_obj['docs']
        form = AddBookToShelfForm()

        return render_template('search.html', results=results, search=search, form=form)


###################### HELPER FUNCTIONS ########################

#helper function
def create_book_obj(key):
    """Creates a book object and commits to database so that when a user
    adds a book to their shelf, the info is easily accessible."""

    response = requests.get(f"https://openlibrary.org/works/{ key }.json")
    json = response.json()

    title = json['title']
    author_names = get_author(json)
    author_string = ', '.join([str(author) for author in author_names])
    
    desc = check_valid_desc(json)
    cover = check_valid_cover(json)

    new_book = Book(
        key=key,
        title=title,
        author_name=author_string,
        description=desc,
        cover=cover
    )

    db.session.add(new_book)
    db.session.commit()


#helper function
def check_valid_desc(json):
    """Parses out a book's description based on the format recieved in the request.

    ***Note***: the json response will either not have a description for books OR
                have a description under the key 'description' OR have a description
                under the nested key 'value' """

    if 'description' not in json.keys():
        desc = "No description available"
    elif type(json['description']) == str:
        desc = json['description']
    else:
        desc = json['description']['value']

    return desc


#helper function
def check_valid_cover(json):
    """Checks if a book has a valid cover."""

    if 'covers' in json:
        cover = json['covers'][0]
    else:
        cover = DEFAULT_COVER_IMG
    
    return cover


#helper function
def get_author(json_obj):
    """Gets author name from author key derived from a piece of work."""

    author_key = []
    authors = []

    #gets author key(s) from json response and appends to a list
    for author in json_obj['authors']:
        author_key.append(author['author']['key'])
    
    #loop through author_key list and send an API request for every key
    ##get author name and append to author list
    for key in author_key:
        response = requests.get(f'https://openlibrary.org/{ key }.json')
        json = response.json()
        authors.append(json['name'])
    
    return authors


#helper function
def get_books_array(shelves):
    """Returns a list of lists. Each nested list is sorted from their status."""
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















