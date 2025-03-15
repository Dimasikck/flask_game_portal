from flask_login import UserMixin
from db import db, MainMenu, Posts, Users
from flask import url_for
from sqlalchemy.orm import Query

class UserLogin(UserMixin):
    def fromDB(self, user_id, db_session):
        self.__user = db_session.query(Users).filter_by(id=user_id).first()
        return self if self.__user else None

    def create(self, user):
        self.__user = user
        return self

    def get_id(self):
        return str(self.__user.id)

    def getName(self):
        return self.__user.name if self.__user else "Без имени"

    def getEmail(self):
        return self.__user.email if self.__user else "Без email"

    def getLogin(self):
        return self.__user.login if self.__user else "Без логина"

    def getAvatar(self, app):
        img = None
        if not self.__user or not hasattr(self.__user, 'avatar') or not self.__user.avatar:
            try:
                with app.open_resource(app.root_path + url_for('static', filename='images/default.png'), "rb") as f:
                    img = f.read()
            except FileNotFoundError as e:
                print("Не найден аватар по умолчанию: " + str(e))
        else:
            img = self.__user.avatar

        return img

    def verifyExt(self, filename):
        ext = filename.rsplit('.', 1)[1]
        if ext in ["png", "PNG", "gif", "GIF", "jpg", "jpeg"]:
            return True
        return False