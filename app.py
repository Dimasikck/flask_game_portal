import os
import base64
from flask import Flask, render_template, url_for, request, flash, session, redirect, abort, g, make_response, send_from_directory, send_file, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, asc, desc
from db import *
from forms import *
from UserLogin import UserLogin
from admin.admin import admin
from flask_mail import Mail, Message
import secrets
from config import MAIL_CONFIG, GENRES
from apscheduler.schedulers.background import BackgroundScheduler
import logging

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

# Применение конфигурации Flask-Mail
app.config.update(MAIL_CONFIG)

app.config['RECAPTCHA_PUBLIC_KEY'] = '6LdDuyUrAAAAALDFJcsWCXcaK4ceL6Do31H2r50N'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6LdDuyUrAAAAADuocsxQSu6dvo22oMgEshfzzJvQ'
app.config['RECAPTCHA_OPTIONS'] = {'theme': 'light'}

# Инициализация Flask-Mail
mail = Mail(app)

db.init_app(app)
migrate = Migrate(app, db)
app.register_blueprint(admin, url_prefix='/admin')

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "success"

def generate_token():
    return secrets.token_urlsafe(32)

def send_confirmation_email(user_email, token):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    msg = Message("Подтверждение регистрации", recipients=[user_email])
    msg.body = f"Перейдите по ссылке для подтверждения вашей учетной записи: {confirm_url}"
    msg.html = f"<p>Перейдите по ссылке для подтверждения вашей учетной записи: <a href='{confirm_url}'>{confirm_url}</a></p>"
    mail.send(msg)

def send_password_reset_email(user_email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message("Сброс пароля", recipients=[user_email])
    msg.body = f"Перейдите по ссылке для сброса пароля: {reset_url}"
    msg.html = f"<p>Перейдите по ссылке для сброса пароля: <a href='{reset_url}'>{reset_url}</a></p>"
    mail.send(msg)


def clean_inactive_users():
    try:
        with app.app_context():
            now = datetime.now(timezone.utc)
            # Находим токены подтверждения, срок действия которых истек
            expired_tokens = Token.query.filter(
                Token.type == "email_confirmation",
                Token.expires_at < now
            ).all()

            deleted_users = 0
            deleted_tokens = 0
            for token in expired_tokens:
                user = Users.query.get(token.user_id)
                if user and not user.is_active:
                    # Удаляем связанные записи (Comments, CommentLikes, GameStats, Favorites, Tokens)
                    Comments.query.filter_by(user_id=user.id).delete()
                    CommentLikes.query.filter_by(user_id=user.id).delete()
                    GameStats.query.filter_by(user_id=user.id).delete()
                    Favorites.query.filter_by(user_id=user.id).delete()
                    Token.query.filter_by(user_id=user.id).delete()
                    # Удаляем пользователя
                    db.session.delete(user)
                    deleted_users += 1
                deleted_tokens += 1

            db.session.commit()
            logging.info(f"Cleaned {deleted_users} inactive users and {deleted_tokens} expired tokens")
            return {"users_deleted": deleted_users, "tokens_deleted": deleted_tokens}
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cleaning inactive users: {str(e)}")
        return {"error": str(e)}


#-----------------------------------------------------------------------------------------------------------------

"""
                            Функции для проверки авторизации пользователя в сессии, кодирования изображения,
                            вывода страниц ненайдено и пользователь не авторизован
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
    if current_user.is_authenticated:
        user = Users.query.get(current_user.get_id())
        if user is None:
            logout_user()
            flash("Ваша учетная запись была удалена.", "error")
            return redirect(url_for('login'))
@app.before_request
def check_user_is_action():
    if current_user.is_active:
        user = Users.query.get(current_user.get_id())
        if user is None:
            logout_user()
            flash("Ваша учетная запись не активирована. Пожалуйста, войдите в свою электронную почту и активируйте учетную запись.", "error")
            return redirect(url_for('login'))
@app.template_filter('b64encode')
def b64encode(data):
    if data is None:
        return ""
    return base64.b64encode(data).decode('utf-8')

@app.template_filter('format_time')
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours}ч {minutes}м {seconds}с"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')

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
        posts = Posts.query.order_by(desc(Posts.time)).all()
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
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort_name', 'time_desc')
        filter_type = request.args.get('type_filter', '')
        filter_genre = request.args.get('genre_filter', '')
        filter_favorite = request.args.get('favorite_filter', '')

        query = Games.query
        if search:
            query = query.filter(
                (Games.title.ilike(f'%{search}%')) |
                (Games.description.ilike(f'%{search}%'))
            )
        if filter_type:
            query = query.filter(Games.type == filter_type)
        if filter_genre:
            query = query.filter(Games.genre == filter_genre)
        if filter_favorite == 'favorite':
            query = query.join(Favorites, Favorites.game_id == Games.id).filter(Favorites.user_id == current_user.get_id())

        if sort == 'title_asc':
            query = query.order_by(asc(Games.title))
        elif sort == 'title_desc':
            query = query.order_by(desc(Games.title))
        elif sort == 'time_asc':
            query = query.order_by(asc(Games.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Games.time))
        else:
            query = query.order_by(desc(Games.time))

        games = query.all()
        favorite_game_ids = [fav.game_id for fav in Favorites.query.filter_by(user_id=current_user.get_id()).all()]
    except Exception as e:
        flash(f'Ошибка получения списка игр: {str(e)}', 'error')
        games = []
        favorite_game_ids = []
    return render_template('listgames.html', title="Игры", menu=menu, games=games,
                          search=search, sort=sort, filter_type=filter_type, filter_genre=filter_genre,
                          filter_favorite=filter_favorite, genres=GENRES, favorite_game_ids=favorite_game_ids)
#-----------------------------------------------------------------------------------------------------------------

"""
                                      Маршрут страницы СПИСКА ПОСТОВ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/listposts', methods=['GET'])
@login_required
def listposts():
    menu = MainMenu.query.all()
    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort_name', 'time_desc')

        query = Posts.query
        if search:
            query = query.filter(
                (Posts.title.ilike(f'%{search}%')) |
                (Posts.annonce.ilike(f'%{search}%'))
            )

        if sort == 'title_asc':
            query = query.order_by(asc(Posts.title))
        elif sort == 'title_desc':
            query = query.order_by(desc(Posts.title))
        elif sort == 'time_asc':
            query = query.order_by(asc(Posts.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Posts.time))
        else:
            query = query.order_by(desc(Posts.time))

        posts = query.all()
    except Exception as e:
        flash(f'Ошибка получения списка постов: {str(e)}', 'error')
        posts = []
    return render_template('listposts.html', title="Посты", menu=menu, posts=posts,
                          search=search, sort=sort)
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
    is_favorite = Favorites.query.filter_by(user_id=current_user.get_id(), game_id=game_id).first() is not None

    response = make_response(render_template('game.html', menu=menu, title=game.title, game=game, is_favorite=is_favorite))
    if game.type == 'link':
        response.set_cookie('game_path', '', path='/', samesite='Lax')
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
            if not user.is_active:
                flash("Ваша учетная запись не подтверждена. Проверьте почту для подтверждения.", "error")
                return render_template("login.html", menu=MainMenu.query.all(), title="Авторизация", form=form)
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
        new_user = Users(
            login=form.login.data.lower(),
            name=form.name.data,
            email=form.email.data.lower(),
            psw=hash_psw,
            time=int(datetime.now(timezone.utc).timestamp()),
            is_active=False,
            receive_notifications = True
        )
        db.session.add(new_user)
        db.session.flush()

        token = generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        confirmation_token = Token(
            user_id=new_user.id,
            token=token,
            type="email_confirmation",
            expires_at=expires_at
        )
        db.session.add(confirmation_token)
        db.session.commit()

        send_confirmation_email(new_user.email, token)
        flash("Письмо с подтверждением отправлено на вашу почту.", "success")
        return redirect(url_for('login'))
    return render_template("register.html", menu=MainMenu.query.all(), title="Регистрация", form=form)

#-----------------------------------------------------------------------------------------------------------------

"""
                                    Маршрут для ПОДТВЕРЖДЕНИЯ EMAIL
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/confirm_email/<token>")
def confirm_email(token):
    token_record = Token.query.filter_by(token=token, type="email_confirmation").first()
    if not token_record:
        flash("Ссылка недействительна.", "error")
        return redirect(url_for('register'))

    expires_at_aware = token_record.expires_at.replace(tzinfo=timezone.utc)
    if expires_at_aware < datetime.now(timezone.utc):
        flash("Срок действия ссылки истек.", "error")
        return redirect(url_for('register'))

    user = Users.query.get(token_record.user_id)
    if not user:
        flash("Пользователь не найден.", "error")
        return redirect(url_for('register'))

    user.is_active = True
    db.session.delete(token_record)
    db.session.commit()
    flash("Ваша учетная запись успешно подтверждена!", "success")
    return redirect(url_for('login'))

#-----------------------------------------------------------------------------------------------------------------

"""
                                    Маршрут для СБРОСА ПАРОЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/reset_password/<token>", methods=["POST", "GET"])
def reset_password(token):
    token_record = Token.query.filter_by(token=token, type="password_reset").first()
    if not token_record:
        flash("Ссылка недействительна.", "error")
        return redirect(url_for('forgot_password'))

    expires_at_aware = token_record.expires_at.replace(tzinfo=timezone.utc)
    if expires_at_aware < datetime.now(timezone.utc):
        flash("Срок действия ссылки истек.", "error")
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = Users.query.get(token_record.user_id)
        if user:
            user.psw = generate_password_hash(form.password.data)
            user.is_active = True
            db.session.delete(token_record)
            db.session.commit()
            flash("Пароль успешно изменен. Войдите с новым паролем.", "success")
            return redirect(url_for('login'))
        else:
            flash("Пользователь не найден.", "error")
    return render_template("reset_password.html", menu=MainMenu.query.all(), title="Сброс пароля", form=form, token=token)

#-----------------------------------------------------------------------------------------------------------------

"""
                                    Маршрут для ФОРМЫ "ЗАБЫЛ ПАРОЛЬ"
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route("/forgot_password", methods=["POST", "GET"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            reset_token = Token(
                user_id=user.id,
                token=token,
                type="password_reset",
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            send_password_reset_email(user.email, token)
            flash("Письмо для сброса пароля отправлено на вашу почту.", "success")
        else:
            flash("Пользователь с такой почтой не найден.", "error")
        return redirect(url_for('login'))
    return render_template("forgot_password.html", menu=MainMenu.query.all(), title="Восстановление пароля", form=form)

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

@app.route('/post/<int:post_id>/comments')
@login_required
def get_post_comments(post_id):
    comments = Comments.query.filter_by(post_id=post_id, game_id=None, parent_id=None).order_by(Comments.timestamp.desc()).all()
    current_user_id = int(current_user.get_id())

    def serialize_comment(comment):
        return {
            "id": comment.id,
            "user": comment.user.name,
            "user_id": comment.user_id,  # Добавляем ID пользователя для ссылки на профиль
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

    comment = Comments(
        user_id=current_user.get_id(),
        post_id=post_id,
        game_id=None,
        text=text,
        parent_id=parent_id
    )
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
    stats = GameStats.query.filter_by(user_id=current_user.get_id()).order_by(GameStats.last_played.desc()).all()
    favorites = Favorites.query.filter_by(user_id=current_user.get_id()).order_by(Favorites.added_at.desc()).all()
    return render_template("profile.html", menu=menu, title="Профиль", stats=stats, favorites=favorites)

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут страницы ПРОФИЛЯ ДРУГОГО ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    user = Users.query.get_or_404(user_id)
    if not user.is_active:
        flash("Этот пользователь не активирован.", "error")
        return redirect(url_for('index'))
    menu = MainMenu.query.all()
    stats = GameStats.query.filter_by(user_id=user_id).order_by(GameStats.last_played.desc()).all()
    favorites = Favorites.query.filter_by(user_id=user_id).order_by(Favorites.added_at.desc()).all()
    return render_template("user_profile.html", menu=menu, title=f"Профиль {user.name}", user=user, stats=stats, favorites=favorites)

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут страницы РЕДАКТИРОВАНИЯ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ на сайте
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/edit_profile.html', methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    form.user_id = current_user.get_id()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            updates = {}
            if form.name.data and form.name.data != current_user.getName():
                updates['name'] = form.name.data
            if form.email.data and form.email.data != current_user.getEmail():
                updates['email'] = form.email.data
            if form.password.data:
                updates['psw'] = generate_password_hash(form.password.data)
            updates['receive_notifications'] = form.receive_notifications.data
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
                        flash('Ошибка обновления аватара', 'error')
            if updates or form.avatar.data:
                flash('Профиль успешно обновлен','success')
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f'Ошибка при обновлении профиля: {str(e)}', 'error')
    form.name.data = current_user.getName()
    form.email.data = current_user.getEmail()
    form.receive_notifications.data = current_user.getReceiveNotifications()
    menu = MainMenu.query.all()
    return render_template("edit_profile.html", menu=menu, title="Редактирование профиля", form=form)

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут для ПОЛУЧЕНИЯ И ОТОБРАЖЕНИЯ АВАТАРА ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/userava')
@login_required
def userava():
    img = current_user.getAvatar(app)
    if img:
        h = make_response(img)
        h.headers['Content-Type'] = 'image/png'
        return h
    return ""

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут для ОБНОВЛЕНИЯ АВАТАРА ПОЛЬЗОВАТЕЛЯ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/upload', methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()
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
    comments = Comments.query.filter_by(game_id=game_id, post_id=None, parent_id=None).order_by(Comments.timestamp.desc()).all()
    current_user_id = int(current_user.get_id())

    def serialize_comment(comment):
        return {
            "id": comment.id,
            "user": comment.user.name,
            "user_id": comment.user_id,  # Добавляем ID пользователя для ссылки на профиль
            "avatar": f"data:image/png;base64,{base64.b64encode(comment.user.avatar).decode('utf-8')}" if comment.user.avatar else None,
            "text": comment.text,
            "timestamp": comment.timestamp.strftime('%Y-%m-%d %H:%M'),
            "likes": comment.likes,
            "is_owner": comment.user_id == current_user_id,
            "replies": [serialize_comment(reply) for reply in comment.replies]
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
    parent_id = data.get('parent_id')

    if not text:
        return {"error": "Комментарий не может быть пустым"}, 400

    comment = Comments(
        user_id=current_user.get_id(),
        game_id=game_id,
        post_id=None,
        text=text,
        parent_id=parent_id
    )
    db.session.add(comment)
    db.session.commit()
    return {"message": "Комментарий добавлен"}

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут для ПОЛУЧЕНИЯ ЛАЙКА К КОММЕНТАРИЮ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comments.query.get_or_404(comment_id)
    existing_like = CommentLikes.query.filter_by(user_id=current_user.get_id(), comment_id=comment_id).first()
    if existing_like:
        db.session.delete(existing_like)
        comment.likes -= 1
    else:
        new_like = CommentLikes(user_id=current_user.get_id(), comment_id=comment_id)
        db.session.add(new_like)
        comment.likes += 1
    db.session.commit()
    return {"likes": comment.likes}

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршрут для УДАЛЕНИЯ КОММЕНТАРИЯ
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
                                     Маршруты для ОТСЛЕЖИВАНИЯ ВРЕМЕНИ ИГРЫ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/game/<int:game_id>/track_time', methods=['POST'])
@login_required
def track_time(game_id):
    data = request.json
    time_spent = data.get('time_spent', 0)
    if not isinstance(time_spent, int) or time_spent < 0:
        return {"error": "Некорректное время"}, 400

    stat = GameStats.query.filter_by(user_id=current_user.get_id(), game_id=game_id).first()
    if stat:
        stat.time_spent += time_spent
        stat.last_played = datetime.now(timezone.utc)
    else:
        stat = GameStats(
            user_id=current_user.get_id(),
            game_id=game_id,
            time_spent=time_spent,
            last_played=datetime.now(timezone.utc)
        )
        db.session.add(stat)
    db.session.commit()
    return {"message": "Время обновлено"}

#-----------------------------------------------------------------------------------------------------------------

"""
                                     Маршруты для УПРАВЛЕНИЯ ИЗБРАННЫМИ ИГРАМИ
"""
#-----------------------------------------------------------------------------------------------------------------
@app.route('/game/<int:game_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(game_id):
    favorite = Favorites.query.filter_by(user_id=current_user.get_id(), game_id=game_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return {"message": "Игра удалена из избранного", "is_favorite": False}
    else:
        new_favorite = Favorites(
            user_id=current_user.get_id(),
            game_id=game_id,
            added_at=datetime.now(timezone.utc)
        )
        db.session.add(new_favorite)
        db.session.commit()
        return {"message": "Игра добавлена в избранное", "is_favorite": True}

#-----------------------------------------------------------------------------------------------------------------

"""
                                               ЗАПУСК ВЕБ ПРИЛОЖЕНИЯ
"""
#-----------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Создание таблиц при запуске
        # Очистка неактивированных пользователей при запуске
        result = clean_inactive_users()
        logging.info(f"Initial cleanup: {result}")

    # Настройка планировщика для автоматической очистки
    scheduler = BackgroundScheduler()
    scheduler.add_job(clean_inactive_users, 'interval', days=1, id='clean_inactive_users')
    scheduler.start()

    try:
        app.run(port=5001)
        # app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()