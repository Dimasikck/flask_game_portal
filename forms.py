
from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from db import Users
import re
# ----------------------------------------------------------------------------------------------------------------
"""
                                Класс формы для СТРАНИЦЫ АВТОРИЗАЦИИ ПОЛЬЗОВАТЕЛЯ 
"""
#-----------------------------------------------------------------------------------------------------------------
class LoginForm(FlaskForm):
    login = StringField("Login: ", validators=[DataRequired(),
                                                Length(min=4, max=20, message="Логин должен быть от 4 до 20 символов")])
    psw = PasswordField("Пароль: ", validators=[DataRequired(),
                                                Length(min=4, max=100, message="Пароль должен быть от 4 до 100 символов")])
    remember = BooleanField("Запомнить", default=False)
    recaptcha = RecaptchaField()  # Поле reCAPTCHA
    submit = SubmitField("Войти", render_kw={'class': 'login_button'})
# ----------------------------------------------------------------------------------------------------------------
"""
                               Класс формы для СТРАНИЦЫ РЕГИСТРАЦИИ ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
class RegisterForm(FlaskForm):
    login = StringField("Логин: ", validators=[Length(min=4, max=20, message="Логин должен быть от 4 до 20 символов")])
    name = StringField("Имя: ", validators=[Length(min=4, max=100, message="Имя должно быть от 4 до 100 символов")])
    email = StringField("Email: ", validators=[Email("Некорректный email")])
    psw = PasswordField("Пароль: ", validators=[DataRequired(),
                                               Length(min=4, max=100, message="Пароль должен быть от 4 до 100 символов")])
    psw2 = PasswordField("Повтор пароля: ", validators=[DataRequired(), EqualTo('psw', message="Пароли не совпадают")])
    recaptcha = RecaptchaField()  # Поле reCAPTCHA
    submit = SubmitField("Регистрация", render_kw={'class': 'login_button'})

    def validate_login(self, field):
        if Users.query.filter_by(login=field.data).first():
            raise ValidationError("Пользователь с таким логином уже зарегистрирован.")

        if not re.match(r'^[a-zA-Z0-9_]+$', field.data):
            raise ValidationError("Логин может содержать только латинские буквы, цифры и символ подчеркивания (_).")

    def validate_name(self, field):
        if field.data and field.data != '':
            if not re.match(r'^[a-zA-Zа-яА-Я0-9\s]+$', field.data):
                raise ValidationError("Имя может содержать только буквы, цифры и пробел.")

    def validate_email(self, field):
        if Users.query.filter_by(email=field.data).first():
            raise ValidationError("Пользователь с такой почтой уже зарегистрирован.")
# -----------------------------------------------------------------------------------------------------------------
"""
                               Класс формы для СТРАНИЦЫ РЕДАКТИРОВАНИЯ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
class EditProfileForm(FlaskForm):

    name = StringField("Имя: ", validators=[Optional(), Length(min=4, max=100, message="Имя должно быть от 4 до 100 символов")])
    email = StringField("Email: ", validators=[Optional(), Email("Некорректный email")])
    password = PasswordField("Новый пароль: ", validators=[Optional(),
                                               Length(min=4, max=100, message="Пароль должен быть от 4 до 100 символов")])
    password_confirm = PasswordField("Повтор пароля: ", validators=[Optional(), EqualTo('password', message="Пароли не совпадают")])
    avatar = FileField('Новый аватар', validators=[FileAllowed(['gif','png','jpg','jpeg'], 'Разрешены только изображения GIF, PNG, или JPEG')])
    submit = SubmitField("Сохранить", render_kw={'class': 'btn btn-save' })

    def validate_name(self, field):
        if field.data and field.data != '':
            if not re.match(r'^[a-zA-Zа-яА-Я0-9\s]+$', field.data):
                raise ValidationError("Имя может содержать только буквы, цифры и пробел.")

    def validate_email(self, field):
        if field.data and field.data != '':
            from flask_login import  current_user
            if Users.query.filter(Users.email == field.data, Users.id != current_user.get_id()).first():
                raise ValidationError("Этот почта используется другим пользователем.")

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Отправить письмо')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[
        DataRequired(),
        Length(min=6, message="Пароль должен содержать минимум 6 символов")
    ])
    password_confirm = PasswordField('Подтвердите пароль', validators=[
        DataRequired(),
        EqualTo('password', message="Пароли должны совпадать")
    ])
    submit = SubmitField('Сбросить пароль')