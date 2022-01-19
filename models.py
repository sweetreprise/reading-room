"""SQLAlchemy models for Reading Room"""

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from datetime import datetime

bcrypt = Bcrypt()
# connect to the PostgreSQL database
db = SQLAlchemy()

# default cover image for books without a cover photo available
DEFAULT_COVER_IMG = "/static/images/default-book.png"
DEFAULT_USER_IMG = "/static/images/default-user.jpeg"

def connect_db(app):
    """Connect db to flask app"""

    db.app = app
    db.init_app(app)

#########################################################
# Models

class User(db.Model, UserMixin):
    """User class"""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    username = db.Column(
        db.String(20),
        nullable=False,
        unique=True
    )
    password = db.Column(
        db.Text,
        nullable=False
    )
    first_name = db.Column(
        db.String(30),
        nullable=False
    )
    last_name = db.Column(
        db.String(30),
        nullable=False
    )
    description = db.Column(
        db.Text,
        default=None
    )
    image_url = db.Column(
        db.Text,
        default=DEFAULT_USER_IMG
    )
    
    # User relationships
    favourites = db.relationship(
        'Book',
        secondary="favourites"
    )

    def __repr__(self):
        """Provides some helpful representation about the user when printed."""

        return f"<User #{self.id}: {self.username}"
    
    @classmethod
    def register(cls, username, first_name, last_name, password):
        """Register a user, hashes password"""

        hashed_password = bcrypt.generate_password_hash(password).decode('UTF-8')

        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=hashed_password
        )
        db.session.add(new_user)
        return new_user
    
    @classmethod
    def authenticate(cls, username, password):
        """Searches DB for submitted username and password;
        returns False if match is not found."""

        user = cls.query.filter_by(username=username).first()

        if user:
            if bcrypt.check_password_hash(user.password, password):
                return user
        return False

    def check_unique_username(self, username):
        """Searches DB for submitted username. Returns False if no match is found, returns True if match is found"""

        if self.username == username:
            return False

        user = User.query.filter_by(username=username).first()

        if user:
            return True
        return False

class Author(db.Model):
    """Author class"""

    __tablename__ = 'authors'

    key = db.Column(
        db.String(30),
        primary_key=True
    )
    name = db.Column(
        db.String(50),
        nullable=False
    )

class Book(db.Model):
    """Book class"""

    __tablename__ = 'books'

    key = db.Column(
        db.String(30),
        primary_key=True
    )
    title = db.Column(
        db.String(100),
        nullable=False
    )
    author_key = db.Column(
        db.String(30),
        db.ForeignKey('authors.key', ondelete='cascade'),
        nullable=False
    )
    description = db.Column(
        db.Text,
        nullable=False
    )
    publish_date = db.Column(
        db.String(30),
        nullable=False
    )
    cover = db.Column(
        db.Text,
        default=DEFAULT_COVER_IMG
    )


class Shelf(db.Model):
    """Model for a book a user is either:
    reading, wants-to-read, or finished reading"""

    __tablename__ = 'shelves'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        primary_key=True
    )
    book_key = db.Column(
        db.String(30),
        db.ForeignKey('books.key', ondelete='cascade'),
        nullable=False
    )
    # options for statuses here will be: reading, finished, future reads
    status = db.Column(
        db.String(20),
        nullable=False
    )
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )
    num_pages = db.Column(
        db.Integer
    )
    # value for progress will be a numerical value denoting a percentage of a book read
    progress = db.Column(
        db.Integer,
        default=0
    )
    

class Favourite(db.Model):
    """Class for a user's favourite books"""

    __tablename__ = "favourites"

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade')
    )
    book_key = db.Column(
        db.Text,
        db.ForeignKey('books.key', ondelete='cascade')
    )

class Request(db.Model):
    """Connection between two users. Friends can see specific
    information about each other"""

    __tablename__ = "requests"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    user_a_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )
    user_b_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )
    status = db.Column(
        db.String(15),
        nullable=False
    )

    user_a = db.relationship('User', foreign_keys=[user_a_id], backref="sent_requests")
    user_b = db.relationship('User', foreign_keys=[user_b_id], backref="received_requests")
