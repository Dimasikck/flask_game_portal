from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app and enable foreign keys for SQLite."""
    db.init_app(app)
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def enable_sqlite_fk(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.close()

class MainMenu(db.Model):
    __tablename__ = 'mainmenu'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<MainMenu {self.id}, {self.title},{self.url}>"

class Posts(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    cover = db.Column(db.LargeBinary, nullable=True)
    text = db.Column(db.Text, nullable=False)
    time = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.utcnow().timestamp()))
    comments = db.relationship('Comments', back_populates='post', cascade="all, delete", passive_deletes=True)

    def __repr__(self):
        return f"<Posts {self.id}, {self.title}>"

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    psw = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.LargeBinary, default=None)
    time = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.utcnow().timestamp()))
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    comments = db.relationship('Comments', back_populates='user', cascade="all, delete-orphan", passive_deletes=True)
    comment_likes = db.relationship('CommentLikes', back_populates='user', cascade="all, delete-orphan", passive_deletes=True)
    game_stats = db.relationship('GameStats', back_populates='user', cascade="all, delete-orphan", passive_deletes=True)
    favorites = db.relationship('Favorites', back_populates='user', cascade="all, delete-orphan", passive_deletes=True)
    tokens = db.relationship('Token', back_populates='user', cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Users {self.id}, {self.login},{self.name}, {self.email}, {self.avatar}>"

    @staticmethod
    def updateUser(user_id, **kwargs):
        """Update user attributes by ID."""
        user = Users.query.get(user_id)
        if not user:
            raise Exception('Пользователь не найден')
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.session.commit()
        return True

    @staticmethod
    def updateUserAvatar(avatar, user_id):
        """Update user avatar by ID."""
        if not avatar:
            return False
        try:
            binary = sqlite3.Binary(avatar)
            user = Users.query.get(user_id)
            if user:
                user.avatar = binary
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка обновления аватара в БД: {e}")
            return False

class Games(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    cover = db.Column(db.LargeBinary, nullable=False)
    link = db.Column(db.Text, nullable=False)
    genre = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), nullable=False, default='link')
    installer = db.Column(db.Text, nullable=True)
    time = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.utcnow().timestamp()))
    favorites = db.relationship('Favorites', back_populates='game', cascade="all, delete-orphan", passive_deletes=True)
    stats = db.relationship('GameStats', back_populates='game', cascade="all, delete-orphan", passive_deletes=True)
    comments = db.relationship('Comments', back_populates='game', cascade="all, delete", passive_deletes=True)

    def __repr__(self):
        return f"<Games {self.id}, {self.title}>"

    @staticmethod
    def clean_orphaned_records():
        """Remove orphaned records in Favorites and GameStats that reference non-existent games."""
        try:
            favorites_deleted = Favorites.query.filter(~Favorites.game_id.in_(db.session.query(Games.id))).delete()
            stats_deleted = GameStats.query.filter(~GameStats.game_id.in_(db.session.query(Games.id))).delete()
            db.session.commit()
            return {"favorites_deleted": favorites_deleted, "stats_deleted": stats_deleted}
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка очистки осиротевших записей: {e}")
            return {"error": str(e)}

class Comments(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id', ondelete='CASCADE'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    likes = db.Column(db.Integer, default=0)
    user = db.relationship('Users', back_populates='comments', passive_deletes=True)
    game = db.relationship('Games', back_populates='comments')
    post = db.relationship('Posts', back_populates='comments')
    parent = db.relationship('Comments', remote_side=[id], backref=db.backref('replies', lazy=True, cascade="all, delete"))
    comment_likes = db.relationship('CommentLikes', back_populates='comment', cascade="all, delete")

    def __repr__(self):
        return f"<Comment {self.id}, User {self.user_id}, Game {self.game_id}, Post {self.post_id}>"

class CommentLikes(db.Model):
    __tablename__ = 'comment_likes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('Users', back_populates='comment_likes', passive_deletes=True)
    comment = db.relationship('Comments', back_populates='comment_likes')

    def __repr__(self):
        return f"<CommentLike {self.id}, User {self.user_id}, Comment {self.comment_id}>"

class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(100), nullable=False, unique=True)
    type = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship('Users', back_populates='tokens')

    def __repr__(self):
        return f"<Token {self.id}, User {self.user_id}, Type {self.type}>"

class GameStats(db.Model):
    __tablename__ = 'game_stats'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    time_spent = db.Column(db.Integer, nullable=False, default=0)  # Время в секундах
    last_played = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    user = db.relationship('Users', back_populates='game_stats')
    game = db.relationship('Games', back_populates='stats')

    def __repr__(self):
        return f"<GameStats {self.id}, User {self.user_id}, Game {self.game_id}, Time {self.time_spent}>"

class Favorites(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    user = db.relationship('Users', back_populates='favorites')
    game = db.relationship('Games', back_populates='favorites')

    def __repr__(self):
        return f"<Favorites {self.id}, User {self.user_id}, Game {self.game_id}>"