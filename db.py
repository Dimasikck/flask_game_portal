from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection
"""
                                       Создание объекта БД SQLAlchemy
"""
#-----------------------------------------------------------------------------------------------------------------
db = SQLAlchemy()
def init_app(app):
    db.init_app(app)

    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def enable_sqlite_fk(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.close()


#-----------------------------------------------------------------------------------------------------------------
"""
                                    Класс таблицы в БД ПУНКТОВ МЕНЮ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
class MainMenu(db.Model):
    __tablename__ = 'mainmenu'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<MainMenu {self.id}, {self.title},{self.url}>"
#-----------------------------------------------------------------------------------------------------------------
"""
                                             Класс таблицы ПОСТОВ в БД 
"""
#-----------------------------------------------------------------------------------------------------------------
class Posts(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    time = db.Column(db.Integer, nullable=False, default=datetime.utcnow)  # Добавлено поле времени

    def __repr__(self):
        return f"<Posts {self.id}, {self.title}>"
#-----------------------------------------------------------------------------------------------------------------
"""
                                      Класс таблицы ПОЛЬЗОВАТЕЛЕЙ в БД 
"""
#-----------------------------------------------------------------------------------------------------------------
class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    psw = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.LargeBinary, default=None)
    time = db.Column(db.Integer, nullable=False, default=datetime.utcnow)  # Добавлено поле времени
    comments = db.relationship('Comments', cascade="all, delete-orphan", passive_deletes=True)
    comment_likes = db.relationship('CommentLikes', cascade="all, delete-orphan", passive_deletes=True)
    def __repr__(self):
        return f"<Users {self.id}, {self.login},{self.name}, {self.email}, {self.avatar}>"

    @staticmethod
    def updateUser(user_id, **kwargs):
        user = Users.query.get(user_id)
        if not user:
            raise Exception('Пользователь не найден')
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.session.commit()
        return True


    @staticmethod
    def updateUserAvatar(avatar, user_id):
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
# ----------------------------------------------------------------------------------------------------------------
"""
                                            Класс таблицы ИГР в БД 
"""
#-----------------------------------------------------------------------------------------------------------------
class Games(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    cover = db.Column(db.LargeBinary, nullable=False)  # Ссылка на обложку
    link = db.Column(db.Text, nullable=False)  # HTML ссылка на игру
    time = db.Column(db.Integer, nullable=False, default=datetime.utcnow)  # Добавлено поле времени

    def __repr__(self):
        return f"<Games {self.id}, {self.title}>"
# ----------------------------------------------------------------------------------------------------------------
"""
                                        Класс таблицы КОМЕНТАРИЕВ в БД 
"""
#-----------------------------------------------------------------------------------------------------------------
class Comments(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)

    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)

    # Добавляем passive_deletes=True
    user = db.relationship('Users', passive_deletes=True)
    game = db.relationship('Games', backref=db.backref('comments', lazy=True, cascade="all, delete"))
    parent = db.relationship('Comments', remote_side=[id],
                             backref=db.backref('replies', lazy=True, cascade="all, delete"))

    def __repr__(self):
        return f"<Comment {self.id}, User {self.user_id}, Game {self.game_id}>"
# ----------------------------------------------------------------------------------------------------------------
"""
                                     Класс таблицы ЛАЙКОВ КОМЕНТАРИЯ в БД 
"""
#-----------------------------------------------------------------------------------------------------------------
class CommentLikes(db.Model):
    __tablename__ = 'comment_likes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=False)

    # Добавляем passive_deletes=True
    user = db.relationship('Users', passive_deletes=True)
    comment = db.relationship('Comments', backref=db.backref('comment_likes', lazy=True))

    def __repr__(self):
        return f"<CommentLike {self.id}, User {self.user_id}, Comment {self.comment_id}>"
#-----------------------------------------------------------------------------------------------------------------