import os
import base64
from flask import Flask, render_template, url_for, request, flash, session, redirect, abort, g, make_response, send_from_directory, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_migrate import Migrate
from sqlalchemy import func, asc, desc
from db import *
from forms import *
from UserLogin import UserLogin
from admin.admin import admin
from git import Repo
import hmac
import hashlib
#-----------------------------------------------------------------------------------------------------------------
"""
                                             Конфигурация Сайта
"""
#-----------------------------------------------------------------------------------------------------------------

SECRET_KEY = '43fswQtodqAAAAAaLYQVnaNOyAwmqeOqWsGPvweqe'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.root_path, 'flask.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

app.config['RECAPTCHA_PUBLIC_KEY'] = '6LdFw-MqAAAAAGIjhuO3UTNYU6gArOpYEbpF3Xb4'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6LdFw-MqAAAAAIQvr_MjNveev2woBtY-uUkDTDjv'
app.config['RECAPTCHA_OPTIONS'] = {'theme': 'light'}

app.app_context().push()

db.init_app(app)
migrate = Migrate(app, db)
app.register_blueprint(admin, url_prefix='/admin')

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "success"

GENRES = (
    '🔫Экшн',
    '🌏Приключения',
    '🧙‍♂️RPG',
    '⚽Спорт',
    '🗿Головоломка',
    '🏃‍♂️Платформер',
    '🚗Гонки',
    '👊Файтинг',
    '🕵️‍♂️Детектив',
    '🧟‍♂️Хоррор',
    '🎮Аркада',
    '🎲Настольная',
    '🎵Музыкальная',
    '✈️Авиасимулятор',
    '🪖Тактика',
    '🃏Карточная',
    '🏰Tower Defense',
    '🌌Космический симулятор',
    '🐉Фэнтези',
    '🤖Научная фантастика',
    '🏹Стелс',
    '👨‍🚀Выживание',
    '🧩Пазл',
    '🛠️Крафтинг',
    '👑Королевская битва',
    '🎯Шутер от первого лица',
    '🧑‍🤝‍🧑Мультиплеер',
    '🕹️Ретро',
    '🏞️Открытый мир',
    'Другое'
)
#-----------------------------------------------------------------------------------------------------------------

"""
                            Функции для проверки авторизации пользователя в сессии, кодирования изображения,
                            вывода странц ненайдено и пользователь не авторизован
"""
#-----------------------------------------------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return UserLogin().fromDB(user_id, db.session)

@app.before_request
def create_tables():
    if not hasattr(g, '_tables_created'):
        db.create_all()
        g._tables_created = True

@app.before_request
def check_user_in_db():
    # Проверяем, авторизован ли пользователь
    if current_user.is_authenticated:
        # Ищем пользователя в базе данных
        user = Users.query.get(current_user.get_id())
        if user is None:
            # Если пользователь не найден, выходим из системы
            logout_user()
            flash("Ваша учетная запись была удалена.", "error")
            return redirect(url_for('login'))

@app.template_filter('b64encode')
def b64encode(data):
    if data is None:
        return ""
    return base64.b64encode(data).decode('utf-8')
@app.errorhandler(404)
def page_not_found(error):
    menu = MainMenu.query.all()
    return render_template('page404.html', title='Страница не найдена', menu=menu)

@app.errorhandler(401)
def unauthorized(error):
    menu = MainMenu.query.all()
    return render_template('page401.html', title='Не авторизованный пользователь', menu=menu)
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Основной маршрут (Главная страница) Сайта
"""
#-----------------------------------------------------------------------------------------------------------------

@app.route("/")
def index():
    menu = MainMenu.query.all()
    try:
        games = Games.query.all()
        posts = Posts.query.order_by(desc(Posts.time)).all()  # Получаем все посты, сортируем по дате
    except Exception as e:
        flash(f"Ошибка получения данных: {str(e)}", "error")
        games = []
        posts = []
    return render_template('index.html', title="Игровой развлекательный портал", menu=menu, user=current_user, games=games, posts=posts)

#-----------------------------------------------------------------------------------------------------------------
"""
                                      Маршрут страницы СПИСКА ИГР на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/listgames', methods=['GET', 'POST'])
@login_required
def listgames():
    menu = MainMenu.query.all()
    try:
        # Получаем параметры запроса
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort_name', 'time_desc')  # По умолчанию сортировка по дате убывания
        filter_type = request.args.get('type_filter', '')  # Фильтр по типу игры
        filter_genre = request.args.get('genre_filter', '')  # Фильтр по жанру
        # Базовый запрос
        query = Games.query
        # Поиск по названию или описанию
        if search:
            query = query.filter(
                (Games.title.ilike(f'%{search}%')) |
                (Games.description.ilike(f'%{search}%'))
            )
        # Фильтрация по типу игры
        if filter_type:
            query = query.filter(Games.type == filter_type)
        # Сортировка
        if filter_genre:
            query = query.filter(Games.genre == filter_genre)
        if sort == 'title_asc':
            query = query.order_by(asc(Games.title))
        elif sort == 'title_desc':
            query = query.order_by(desc(Games.title))
        elif sort == 'time_asc':
            query = query.order_by(asc(Games.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Games.time))
        else:
            query = query.order_by(desc(Games.time))  # По умолчанию

        games = query.all()
    except Exception as e:
        flash(f'Ошибка получения списка игр: {str(e)}', 'error')
        games = []
    return render_template('listgames.html', title="Игры", menu=menu, games=games,
                          search=search, sort=sort, filter_type=filter_type, filter_genre=filter_genre, genres=GENRES)
#-----------------------------------------------------------------------------------------------------------------
"""
                                      Маршрут страницы ИГРЫ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/game/<int:game_id>")
@login_required
def game(game_id):
    game = Games.query.get_or_404(game_id)
    menu = MainMenu.query.all()

    response = make_response(render_template('game.html', menu=menu, title=game.title, game=game))
    if game.type == 'link':
        response.set_cookie('game_path', '', path='/', samesite='Lax')  # Нет пути для внешних ссылок
    elif game.type == 'pygame':
        response.set_cookie('game_path', game.link, path='/', samesite='Lax')
    elif game.type == 'unity':
        response.set_cookie('game_path', game.link, path='/', samesite='Lax')

    return response

#-----------------------------------------------------------------------------------------------------------------
"""
                                             Маршрут для ИГР Pygame
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/pygame')
@login_required
def pygame():
    game_path = f'games/{request.cookies.get("game_path")}/build/web'
    return send_from_directory(os.path.join(app.static_folder, game_path), 'index.html')

@app.route('/<path:path>')
@login_required
def game_static_files(path):
    return send_from_directory(os.path.join(app.static_folder, f'games/{path.removesuffix(".apk")}/build/web'), path)
#-----------------------------------------------------------------------------------------------------------------
"""
                                    Маршрут для скачивания УСТАНОВЩИКА ИГРЫ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/download_installer/<int:game_id>')
@login_required
def download_installer(game_id):
    game = Games.query.get_or_404(game_id)
    if game.installer and os.path.exists(game.installer):
        return send_file(game.installer, as_attachment=True, download_name=f"{game.title}.exe")
    abort(404)
#-----------------------------------------------------------------------------------------------------------------
"""
                                    Маршрут страницы АВТОРИЗАЦИИ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------

@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(login=form.login.data.lower()).first()
        if user and check_password_hash(user.psw, form.psw.data):
            userlogin = UserLogin().create(user)
            login_user(userlogin, remember=form.remember.data)
            return redirect(request.args.get("next") or url_for("profile"))

        flash("Неверная пара логин/пароль", "error")
    return render_template("login.html", menu=MainMenu.query.all(), title="Авторизация", form=form)
#-----------------------------------------------------------------------------------------------------------------
"""
                                    Маршрут страницы РЕГИСТРАЦИИ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/register", methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash_psw = generate_password_hash(form.psw.data)
        new_user = Users(login=form.login.data.lower(),
                         name=form.name.data,
                         email=form.email.data.lower(),
                         psw=hash_psw, time=int(datetime.now().timestamp()))
        db.session.add(new_user)
        db.session.commit()
        flash("Вы успешно зарегистрированы", "success")
        return redirect(url_for('login'))

    return render_template("register.html", menu=MainMenu.query.all(), title="Регистрация", form=form)
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут СТРАНИЦЫ ПОСТА
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/post/<int:post_id>")
@login_required
def showPost(post_id):
    post = Posts.query.get_or_404(post_id)
    menu = MainMenu.query.all()
    return render_template('post.html', menu=menu, title=post.title, post=post)

# Комментарии для постов
@app.route('/post/<int:post_id>/comments')
@login_required
def get_post_comments(post_id):
    comments = Comments.query.filter_by(post_id=post_id, parent_id=None).order_by(Comments.timestamp.desc()).all()
    current_user_id = int(current_user.get_id())
    def serialize_comment(comment):
        return {
            "id": comment.id,
            "user": comment.user.name,
            "avatar": f"data:image/png;base64,{base64.b64encode(comment.user.avatar).decode('utf-8')}" if comment.user.avatar else None,
            "text": comment.text,
            "timestamp": comment.timestamp.strftime('%Y-%m-%d %H:%M'),
            "likes": comment.likes,
            "is_owner": comment.user_id == current_user_id,
            "replies": [serialize_comment(reply) for reply in comment.replies]
        }
    comments_data = [serialize_comment(comment) for comment in comments]
    return {"comments": comments_data}

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_post_comment(post_id):
    data = request.json
    text = data.get('text', '').strip()
    parent_id = data.get('parent_id')
    if not text:
        return {"error": "Комментарий не может быть пустым"}, 400
    comment = Comments(user_id=current_user.get_id(), post_id=post_id, text=text, parent_id=parent_id)
    db.session.add(comment)
    db.session.commit()
    return {"message": "Комментарий добавлен"}
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ВЫХОДА ИЗ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "success")
    return redirect(url_for('login'))
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут страницы ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/profile')
@login_required
def profile():
    menu = MainMenu.query.all()
    return render_template("profile.html", menu=menu, title="Профиль")
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут страницы РЕДАКТИРОВАНИЯ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/edit_profile.html', methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            updates = {}
            if form.name.data and form.name.data != current_user.getName():
                updates['name'] = form.name.data

            if form.email.data and form.email.data != current_user.getEmail():
                updates['email'] = form.email.data

            if form.password.data:
                updates['psw'] = generate_password_hash(form.password.data)

            if updates:
                Users.updateUser(current_user.get_id(), **updates)

            if form.avatar.data:
                avatar = form.avatar.data
                img = avatar.read()
                if len(img) > 2 * 1024 * 1024:
                    flash('Изображение слишком большое (максимум 2Мб)', "error")
                else:
                    success = Users.updateUserAvatar(img, current_user.get_id())
                    if not success:
                        flash('Ошибка обновления аватра', 'error')
            if updates or form.avatar.data:
                flash('Профиль успешно обновлен','success')
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f'Ошибка при обновлении профиля: {str(e)}', 'error')

    form.name.data = current_user.getName()
    form.email.data = current_user.getEmail()

    menu = MainMenu.query.all()
    return render_template("edit_profile.html", menu=menu, title="Редактирование профиля", form = form)
#-----------------------------------------------------------------------------------------------------------------


"""
                                     Маршрут для ПОЛУЧЕНИЯ И ОТОБРАЖЕНИЯ АВТАРА ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/userava')
@login_required
def userava():
    img = current_user.getAvatar(app)  # Используем метод getAvatar из UserLogin
    if img:
        h = make_response(img)
        h.headers['Content-Type'] = 'image/png'
        return h
    return ""
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ОБНОВЛЕНИЯ АВТАРА ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/upload', methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and current_user.verifyExt(file.filename):
            try:
                # Чтение файла в переменную
                img = file.read()

                # Вызов метода для обновления аватара
                success = Users.updateUserAvatar(img, current_user.get_id())

                if not success:
                    flash("Ошибка обновления аватара", "error")
                else:
                    flash("Аватар обновлен", "success")
            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "error")
        else:
            flash("Ошибка обновления аватара", "error")

    return redirect(url_for('profile'))
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ПОЛУЧЕНИЯ СПИСКА КОММЕНТАРИЕВ ИГРЫ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/game/<int:game_id>/comments')
@login_required
def get_comments(game_id):
    comments = Comments.query.filter_by(game_id=game_id, parent_id=None).order_by(Comments.timestamp.desc()).all()
    current_user_id = int(current_user.get_id())

    def serialize_comment(comment):
        return {
            "id": comment.id,
            "user": comment.user.name,
            "avatar": f"data:image/png;base64,{base64.b64encode(comment.user.avatar).decode('utf-8')}" if comment.user.avatar else None,
            "text": comment.text,
            "timestamp": comment.timestamp.strftime('%Y-%m-%d %H:%M'),
            "likes": comment.likes,
            "is_owner": comment.user_id == current_user_id,
            "replies": [serialize_comment(reply) for reply in comment.replies]  # Вложенные комментарии
        }

    comments_data = [serialize_comment(comment) for comment in comments]
    return {"comments": comments_data}
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ДОБАВЛЕНИЯ КОММЕНТАРИЯ К ИГРЕ
"""
#-----------------------------------------------------------------------------------------------------------------

@app.route('/game/<int:game_id>/comment', methods=['POST'])
@login_required
def add_comment(game_id):
    data = request.json
    text = data.get('text', '').strip()
    parent_id = data.get('parent_id')  # ID родительского комментария (если есть)

    if not text:
        return {"error": "Комментарий не может быть пустым"}, 400

    comment = Comments(
        user_id=current_user.get_id(),
        game_id=game_id,
        text=text,
        parent_id=parent_id  # Привязываем к родительскому комментарию
    )
    db.session.add(comment)
    db.session.commit()
    return {"message": "Комментарий добавлен"}
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ПОЛУЧЕНИЯ ЛАЙКА К КОМЕНТАРИЮ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comments.query.get_or_404(comment_id)
    # Проверяем, поставил ли пользователь уже лайк
    existing_like = CommentLikes.query.filter_by(user_id=current_user.get_id(), comment_id=comment_id).first()
    if existing_like:
        # Если лайк уже поставлен, удаляем его и уменьшаем количество лайков
        db.session.delete(existing_like)
        comment.likes -= 1
    else:
        # Если лайк не был поставлен, добавляем новый лайк и увеличиваем количество лайков
        new_like = CommentLikes(user_id=current_user.get_id(), comment_id=comment_id)
        db.session.add(new_like)
        comment.likes += 1
    db.session.commit()
    return {"likes": comment.likes}
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для УДАЛЕНИЯ К КОМЕНТАРИЯ
"""
#-----------------------------------------------------------------------------------------------------------------

@app.route('/comment/<int:comment_id>/delete', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comments.query.get_or_404(comment_id)

    if comment.user_id != int(current_user.get_id()):
        return {"error": "Вы можете удалить только свои комментарии"}, 403
    CommentLikes.query.filter_by(comment_id=comment_id).delete()

    db.session.delete(comment)
    db.session.commit()
    return {"success": True}



#-----------------------------------------------------------------------------------------------------------------
"""
                                               ЗАПУСК ВЕБ ПРИЛОЖЕНИЯ
"""
#-----------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    app.run(port=5001)