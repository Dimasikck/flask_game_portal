import shutil
import zipfile
import base64
from flask import Blueprint, render_template, url_for, redirect, session, request, flash
from werkzeug.utils import secure_filename
import os
from db import db, Posts, Users, Games, MainMenu, Comments, CommentLikes, Favorites, GameStats
from datetime import datetime, timedelta
from sqlalchemy import func, asc, desc
from git import Repo
import hmac
import hashlib
from config import GENRES
from flask_mail import Message

admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

menu = [{'url': '.index', 'title': 'Панель'},
        {'url': '.list_pubs', 'title': 'Список постов'},
        {'url': '.list_games', 'title': 'Список игр'},
        {'url': '.list_users', 'title': 'Список пользователей'},
        {'url': '.list_menu', 'title': 'Пункты меню'},
        {'url': '.logout', 'title': 'Выйти'}]

SECRET_KEY = '43fswQtodqAAAAAaLYQVnaNOyAwmqeOqWsGPvweqe'

def isLogged():
    return True if session.get('admin_logged') else False

def login_admin():
    session['admin_logged'] = 1

def logout_admin():
    session.pop('admin_logged', None)

@admin.route('/')
def index():
    if not isLogged():
        return redirect(url_for('.login'))
    total_users = Users.query.count()
    total_games = Games.query.count()
    today = datetime.now()
    last_week = today - timedelta(days=7)

    user_stats = (
        db.session.query(
            func.date(func.datetime(Users.time, 'unixepoch')),
            func.count()
        )
        .filter(Users.time >= int(last_week.timestamp()))
        .group_by(func.date(func.datetime(Users.time, 'unixepoch')))
        .all()
    )
    game_stats = (
        db.session.query(
            func.date(func.datetime(Games.time, 'unixepoch')),
            func.count()
        )
        .filter(Games.time >= int(last_week.timestamp()))
        .group_by(func.date(func.datetime(Games.time, 'unixepoch')))
        .all()
    )

    user_dates = [str(stat[0]) for stat in user_stats] if user_stats else []
    user_counts = [stat[1] for stat in user_stats] if user_stats else []
    game_dates = [str(stat[0]) for stat in game_stats] if game_stats else []
    game_counts = [stat[1] for stat in game_stats] if game_stats else []

    return render_template(
        'admin/index.html',
        menu=menu,
        title='Админ-панель',
        total_users=total_users,
        total_games=total_games,
        user_dates=user_dates,
        user_counts=user_counts,
        game_dates=game_dates,
        game_counts=game_counts
    )

@admin.route('/update_site', methods=['POST'])
def update_site():
    if not isLogged():
        return redirect(url_for('.login'))

    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    try:
        print("Pulling from Git")
        repo = Repo('/home/flaskgameportal/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')
        print("Git pull successful")
        os.system('touch /var/www/flaskgameportal_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        flash("Сайт успешно обновлен", "success")
    except Exception as e:
        print(f"Error: {str(e)}")
        flash(f"Ошибка обновления сайта: {str(e)}", "error")

    return redirect(url_for('.index'))

@admin.route('/webhook', methods=['POST'])
def webhook():
    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    signature = request.headers.get('X-Hub-Signature-256')
    print(f"Signature: {signature}")
    if not signature:
        print("No signature provided")
        return 'No signature provided', 403

    secret = SECRET_KEY.encode('utf-8')
    hash_object = hmac.new(secret, request.data, hashlib.sha256)
    expected_signature = 'sha256=' + hash_object.hexdigest()
    print(f"Expected signature: {expected_signature}")
    if not hmac.compare_digest(expected_signature, signature):
        print("Invalid signature")
        return 'Invalid signature', 403

    try:
        print("Pulling from Git")
        repo = Repo('/home/flaskgameportal/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')
        print("Git pull successful")
        os.system('touch /var/www/flaskgameportal_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        return 'Updated successfully', 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

@admin.route('/login', methods=["POST", "GET"])
def login():
    if isLogged():
        return redirect(url_for('.index'))

    if request.method == "POST":
        if request.form['user'] == "admin" and hashlib.sha256(request.form['psw'].encode('utf-8')).hexdigest() == "4d8e10cb286552d72ef1869e186afed3e62e60a2fd4fa062006b780730760704":
            login_admin()
            return redirect(url_for('.index'))
        else:
            flash("Неверная пара логин/пароль", "error")

    return render_template('admin/login.html', title='Админ-панель')

@admin.route('/logout', methods=["POST", "GET"])
def logout():
    if not isLogged():
        return redirect(url_for('.login'))

    logout_admin()

    return redirect(url_for('.login'))

@admin.route('/list_pubs')
def list_pubs():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')
        query = Posts.query
        if search:
            query = query.filter(
                (Posts.title.ilike(f'%{search}%')) |
                (Posts.text.ilike(f'%{search}%'))
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
    return render_template('admin/list_pubs.html', title='Список постов', menu=menu, posts=posts,
                          search=search, sort=sort)

@admin.route('/add_post', methods=['POST', 'GET'])
def add_post():
    from app import mail  # Локальный импорт внутри функции
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        text = request.form.get('text')
        cover_file = request.files.get('cover')
        if not title or not text or not cover_file:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                url = secure_filename(title.lower().replace(' ', '-'))
                existing_post = Posts.query.filter_by(url=url).first()
                if existing_post:
                    url = f"{url}-{int(datetime.now().timestamp())}"

                if Posts.query.filter_by(title=title).first():
                    flash('Пост с таким названием уже существует', 'error')
                    return render_template('admin/add_post.html', menu=menu, title='Добавить пост')
                cover_data = cover_file.read()
                new_post = Posts(title=title, url=url, text=text, cover=cover_data,
                                 time=int(datetime.now().timestamp()))
                db.session.add(new_post)
                db.session.commit()

                # Отправка уведомлений всем зарегистрированным пользователям
                users = Users.query.filter_by(is_active=True, receive_notifications=True).all()
                post_url = url_for('showPost', post_id=new_post.id, _external=True)
                cover_b64 = base64.b64encode(cover_data).decode('utf-8')
                for user in users:
                    msg = Message(
                        subject=f"Новый пост: {title}",
                        recipients=[user.email]
                    )
                    msg.html = render_template(
                        'email/post_notification.html',
                        post_title=title,
                        post_text=text[:200] + ('...' if len(text) > 200 else ''),
                        post_url=post_url,
                        cover_b64=cover_b64
                    )
                    try:
                        mail.send(msg)
                    except Exception as e:
                        flash(f"Ошибка отправки письма пользователю {user.email}: {str(e)}", 'error')

                flash('Пост успешно добавлен', 'success')
                return redirect(url_for('.list_pubs'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления поста: {str(e)}', 'error')
    return render_template('admin/add_post.html', menu=menu, title='Добавить пост')

@admin.route('/edit_post/<int:post_id>', methods=['POST', 'GET'])
def edit_post(post_id):
    if not isLogged():
        return redirect(url_for('.login'))
    post = Posts.query.get_or_404(post_id)
    if request.method == 'POST':
        title = request.form.get('title')
        text = request.form.get('text')
        cover_file = request.files.get('cover')
        if not title or not text:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                new_url = secure_filename(title.lower().replace(' ', '-'))
                existing_post_with_url = Posts.query.filter_by(url=new_url).first()
                if existing_post_with_url and existing_post_with_url.id != post_id:
                    new_url = f"{new_url}-{int(datetime.now().timestamp())}"

                existing_post = Posts.query.filter_by(title=title).first()
                if existing_post and existing_post.id != post_id:
                    flash('Пост с таким названием уже существует', 'error')
                    return render_template('admin/edit_post.html', menu=menu, title='Редактировать пост', post=post)

                post.title = title
                post.url = new_url
                post.text = text
                if cover_file and cover_file.filename:
                    cover_data = cover_file.read()
                    post.cover = cover_data
                db.session.commit()
                flash('Пост успешно обновлен', 'success')
                return redirect(url_for('.list_pubs'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка обновления поста: {str(e)}', 'error')
    return render_template('admin/edit_post.html', menu=menu, title='Редактировать пост', post=post)

@admin.route('/delete_post/<int:post_id>', methods=['POST', 'GET'])
def delete_post(post_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        post = Posts.query.get_or_404(post_id)
        Comments.query.filter_by(poste_id=post_id).delete()
        db.session.delete(post)
        db.session.commit()
        flash('Пост успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления поста: {str(e)}', 'error')
    return redirect(url_for('.list_pubs'))

@admin.route('/list_users')
def list_users():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')
        filter_role = request.args.get('role', '')
        query = Users.query
        if search:
            query = query.filter(
                (Users.login.ilike(f'%{search}%')) |
                (Users.name.ilike(f'%{search}%')) |
                (Users.email.ilike(f'%{search}%'))
            )
        if filter_role:
            query = query.filter(Users.role == filter_role)
        if sort == 'login_asc':
            query = query.order_by(asc(Users.login))
        elif sort == 'login_desc':
            query = query.order_by(desc(Users.login))
        elif sort == 'time_asc':
            query = query.order_by(asc(Users.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Users.time))
        else:
            query = query.order_by(desc(Users.time))
        users = query.all()
    except Exception as e:
        flash(f'Ошибка получения пользователей: {str(e)}', 'error')
        users = []

    return render_template('admin/list_users.html', title='Список пользователей', menu=menu, list=users,
                          search=search, sort=sort, filter_role=filter_role)

@admin.route('/list_games')
def list_games():
    if not isLogged():
        return redirect(url_for('.login'))

    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')
        filter_type = request.args.get('type', '')
        filter_genre = request.args.get('genre', '')
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
    except Exception as e:
        flash(f'Ошибка получения списка игр: {str(e)}', 'error')
        games = []

    return render_template('admin/list_games.html', title='Список игр', menu=menu, games=games,
                          search=search, sort=sort, filter_type=filter_type, filter_genre=filter_genre, genres=GENRES)

@admin.route('/list_menu')
def list_menu():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        menu_list = MainMenu.query.all()
    except Exception as e:
        flash(f'Ошибка получения списка меню: {str(e)}', 'error')
        menu_list = []
    return render_template('admin/list_menu.html', title='Пункты меню', menu=menu, menu_list=menu_list)

@admin.route('/add_menu', methods=['POST', 'GET'])
def add_menu():
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')

        if not title or not url:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                new_menu = MainMenu(title=title, url=url)
                db.session.add(new_menu)
                db.session.commit()
                flash('Пункт успешно добавлен', 'success')
                return redirect(url_for('.list_menu'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления пункта: {str(e)}', 'error')
    return render_template('admin/add_menu.html', menu=menu, title='Добавить пункт меню')

@admin.route('/add_game', methods=['POST', 'GET'])
def add_game():
    from app import mail  # Локальный импорт внутри функции
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        genre = request.form.get('genre')
        type = request.form.get('type')
        cover_file = request.files.get('cover')

        if not title or not description or not cover_file:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                if Games.query.filter_by(title=title).first():
                    flash('Игра с таким названием уже добавлена', 'error')
                    return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                cover_data = cover_file.read()
                new_game = Games(title=title, description=description, cover=cover_data, genre=genre, time=int(datetime.now().timestamp()))

                if type == 'link':
                    link = request.form.get('link')
                    if not link:
                        flash('Ссылка для внешней игры обязательна', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                    if Games.query.filter_by(link=link).first():
                        flash('Игра с такой ссылкой уже добавлена', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                    new_game.link = link
                    new_game.type = 'link'
                elif type == 'pygame':
                    pygame_zip = request.files.get('pygame_zip')
                    pygame_installer = request.files.get('pygame_installer')
                    pygame_screenshots_zip = request.files.get('pygame_screenshots_zip')
                    if not pygame_zip:
                        flash('Необходимо загрузить архив с игрой', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)

                    game_folder = secure_filename(pygame_zip.filename).rsplit('.', 1)[0]
                    # game_path = os.path.join('static/games', game_folder)
                    game_path = os.path.join('flask_game_portal/static/games', game_folder)
                    os.makedirs(game_path, exist_ok=True)

                    game_zip_path = os.path.join(game_path, 'pygame.zip')
                    pygame_zip.save(game_zip_path)
                    with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(game_path)
                    os.remove(game_zip_path)

                    if pygame_screenshots_zip:
                        pygame_screenshots_path = os.path.join(game_path, 'screenshots')
                        os.makedirs(pygame_screenshots_path, exist_ok=True)
                        screenshots_zip_path = os.path.join(pygame_screenshots_path, 'screenshots.zip')
                        pygame_screenshots_zip.save(screenshots_zip_path)
                        with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(pygame_screenshots_path)
                        os.remove(screenshots_zip_path)
                    if pygame_installer:
                        installer_path = os.path.join(game_path, f"{game_folder}.exe")
                        pygame_installer.save(installer_path)
                        new_game.installer = installer_path
                    new_game.link = game_folder
                    new_game.type = 'pygame'

                elif type == 'unity':
                    unity_zip = request.files.get('unity_zip')
                    unity_installer = request.files.get('unity_installer')
                    unity_screenshots_zip = request.files.get('unity_screenshots_zip')
                    if not unity_zip:
                        flash('Необходимо загрузить архив с Unity WebGL игрой', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру')
                    game_folder = secure_filename(unity_zip.filename).rsplit('.', 1)[0]
                    # game_path = os.path.join('static/games', game_folder)
                    game_path = os.path.join('flask_game_portal/static/games', game_folder)
                    os.makedirs(game_path, exist_ok=True)
                    game_zip_path = os.path.join(game_path, 'unity.zip')
                    unity_zip.save(game_zip_path)
                    with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(game_path)
                    os.remove(game_zip_path)

                    if unity_screenshots_zip:
                        unity_screenshots_path = os.path.join(game_path, 'screenshots')
                        os.makedirs(unity_screenshots_path, exist_ok=True)
                        screenshots_zip_path = os.path.join(unity_screenshots_path, 'screenshots.zip')
                        unity_screenshots_zip.save(screenshots_zip_path)
                        with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(unity_screenshots_path)
                        os.remove(screenshots_zip_path)
                    if unity_installer:
                        installer_path = os.path.join(game_path, f"{game_folder}.exe")
                        unity_installer.save(installer_path)
                        new_game.installer = installer_path
                    new_game.link = game_folder
                    new_game.type = 'unity'

                db.session.add(new_game)
                db.session.commit()

                # Отправка уведомлений всем зарегистрированным пользователям
                # users = Users.query.filter_by(is_active=True, receive_notifications=True).all()
                # game_url = url_for('game', game_id=new_game.id, _external=True)
                # cover_b64 = base64.b64encode(cover_data).decode('utf-8')
                # for user in users:
                #     msg = Message(
                #         subject=f"Новая игра: {title}",
                #         recipients=[user.email]
                #     )
                #     msg.html = render_template(
                #         'email/game_notification.html',
                #         game_title=title,
                #         game_description=description[:200] + ('...' if len(description) > 200 else ''),
                #         game_url=game_url,
                #         cover_b64=cover_b64,
                #         genre=genre
                #     )
                #     try:
                #         mail.send(msg)
                #     except Exception as e:
                #         flash(f"Ошибка отправки письма пользователю {user.email}: {str(e)}", 'error')

                flash('Игра успешно добавлена', 'success')
                return redirect(url_for('.list_games'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления игры: {str(e)}', 'error')
    return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)

@admin.route('/edit_game/<int:game_id>', methods=["POST", "GET"])
def edit_game(game_id):
    if not isLogged():
        return redirect(url_for('.login'))

    game = Games.query.get(game_id)
    if not game:
        flash("Игра не найдена", "error")
        return redirect(url_for('.list_games'))

    if request.method == "POST":
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        genre = request.form.get('genre')
        type = request.form.get('type')
        cover_file = request.files.get('cover')

        if title or description or (cover_file and cover_file.filename):
            if title and description:
                try:
                    existing_game = Games.query.filter_by(title=title).first()
                    if existing_game and existing_game.id != game_id:
                        flash('Игра с таким названием уже добавлена', 'error')
                        return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру', game=game, genres=GENRES)

                    game.title = title
                    game.description = description
                    game.genre = genre
                    if cover_file and cover_file.filename:
                        cover_data = cover_file.read()
                        game.cover = cover_data

                    if type == 'link':
                        link = request.form.get('link')
                        if not link:
                            flash('Ссылка для внешней игры обязательна', 'error')
                            return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру',
                                                   game=game, genres=GENRES)
                        if Games.query.filter_by(link=link).first() and Games.query.filter_by(
                                link=link).first().id != game_id:
                            flash('Игра с такой ссылкой уже добавлена', 'error')
                            return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру',
                                                   game=game, genres=GENRES)
                        game.link = link
                        game.installer = None
                        game.type = type

                    elif type == 'pygame':
                        pygame_zip = request.files.get('pygame_zip')
                        pygame_installer = request.files.get('pygame_installer')
                        pygame_screenshots_zip = request.files.get('pygame_screenshots_zip')
                        if pygame_zip:
                            old_game_folder = game.link
                            # if old_game_folder and os.path.exists(os.path.join('static/games', old_game_folder)):
                            #     shutil.rmtree(os.path.join('static/games', old_game_folder))
                            if old_game_folder and os.path.exists(os.path.join('flask_game_portal/static/games', old_game_folder)):
                                shutil.rmtree(os.path.join('flask_game_portal/static/games', old_game_folder))

                            game_folder = secure_filename(pygame_zip.filename).rsplit('.', 1)[0]
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)

                            pygame_zip_path = os.path.join(game_path, 'pygame.zip')
                            pygame_zip.save(pygame_zip_path)
                            with zipfile.ZipFile(pygame_zip_path, 'r') as zip_ref:
                                zip_ref.extractall(game_path)
                            os.remove(pygame_zip_path)

                            if pygame_screenshots_zip:
                                screenshots_path = os.path.join(game_path, 'screenshots')
                                os.makedirs(screenshots_path, exist_ok=True)
                                screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                                pygame_screenshots_zip.save(screenshots_zip_path)
                                with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(screenshots_path)
                                os.remove(screenshots_zip_path)
                            game.link = game_folder
                        if pygame_installer:
                            game_folder = game.link if game.link else secure_filename(pygame_zip.filename).rsplit('.', 1)[0]
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)
                            installer_path = os.path.join(game_path, f"{game_folder}.exe")
                            if game.installer and os.path.exists(game.installer):
                                os.remove(game.installer)
                            pygame_installer.save(installer_path)
                            game.installer = installer_path
                        game.type = type

                    elif type == 'unity' and request.files.get('unity_zip'):
                        unity_zip = request.files.get('unity_zip')
                        unity_installer = request.files.get('unity_installer')
                        unity_screenshots_zip = request.files.get('unity_screenshots_zip')
                        if unity_zip:
                            old_game_folder = game.link
                            # if old_game_folder and os.path.exists(os.path.join('static/games', old_game_folder)):
                            #     shutil.rmtree(os.path.join('static/games', old_game_folder))
                            if old_game_folder and os.path.exists(os.path.join('flask_game_portal/static/games', old_game_folder)):
                                shutil.rmtree(os.path.join('flask_game_portal/static/games', old_game_folder))

                            game_folder = secure_filename(unity_zip.filename).rsplit('.', 1)[0]
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)

                            unity_game_zip_path = os.path.join(game_path, 'game.zip')
                            unity_zip.save(unity_game_zip_path)
                            with zipfile.ZipFile(unity_game_zip_path, 'r') as zip_ref:
                                zip_ref.extractall(game_path)
                            os.remove(unity_game_zip_path)

                            if unity_screenshots_zip:
                                screenshots_path = os.path.join(game_path, 'screenshots')
                                os.makedirs(screenshots_path, exist_ok=True)
                                screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                                unity_screenshots_zip.save(screenshots_zip_path)
                                with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(screenshots_path)
                                os.remove(screenshots_zip_path)
                            game.link = game_folder
                        if unity_installer:
                            game_folder = game.link if game.link else secure_filename(unity_zip.filename).rsplit('.', 1)[0]
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)
                            installer_path = os.path.join(game_path, f"{game_folder}.exe")
                            if game.installer and os.path.exists(game.installer):
                                os.remove(game.installer)
                            unity_installer.save(installer_path)
                            game.installer = installer_path
                        game.type = type

                    db.session.commit()
                    flash("Игра успешно обновлена", "success")
                    return redirect(url_for('.list_games'))
                except Exception as e:
                    db.session.rollback()
                    flash(f"Ошибка обновления игры: {str(e)}", "error")
            else:
                flash("Все поля должны быть заполнены", "error")

    return render_template('admin/edit_game.html', menu=menu, title="Редактировать игру", game=game, genres=GENRES)

@admin.route('/delete_user/<int:user_id>', methods=['POST', "GET"])
def delete_user(user_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        user = Users.query.get(user_id)
        if user:
            # Явное удаление связанных записей
            Comments.query.filter_by(user_id=user.id).delete()
            CommentLikes.query.filter_by(user_id=user.id).delete()
            Favorites.query.filter_by(user_id=user.id).delete()
            GameStats.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            flash('Пользователь успешно удален', 'success')
        else:
            flash('Пользователь не найден', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления пользователя: {str(e)}', 'error')
    return redirect(url_for('.list_users'))

@admin.route('/delete-game/<int:game_id>', methods=['POST', "GET"])
def delete_game(game_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        game = Games.query.get(game_id)
        if game:
            if game.link and game.type != 'link':
                # game_folder = game.link.replace('static/games/', '')
                # game_path = os.path.join('static/games', game_folder)
                game_folder = game.link.replace('flask_game_portal/static/games/', '')
                game_path = os.path.join('flask_game_portal/static/games', game_folder)
                if os.path.exists(game_path):
                    shutil.rmtree(game_path)
                    flash(f'Папка игры {game_folder} удалена', 'success')
                else:
                    flash(f'Папка игры {game_folder} не найдена', 'error')

            # Явное удаление связанных записей
            Favorites.query.filter_by(game_id=game_id).delete()
            GameStats.query.filter_by(game_id=game_id).delete()
            Comments.query.filter_by(game_id=game_id).delete()
            db.session.delete(game)
            db.session.commit()
            flash('Игра успешно удалена', 'success')
        else:
            flash('Игра не найдена', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления игры: {str(e)}', 'error')
    return redirect(url_for('.list_games'))

@admin.route('/delete-menu/<int:menu_id>', methods=['POST', "GET"])
def delete_menu(menu_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        menu_list = MainMenu.query.get(menu_id)
        if menu_list:
            db.session.delete(menu_list)
            db.session.commit()
            flash('Пункт успешно удален', 'success')
        else:
            flash('Пункт не найден', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления пункта: {str(e)}', 'error')
    return redirect(url_for('.list_menu'))

@admin.route('/edit_menu/<int:menu_id>', methods=["POST", "GET"])
def edit_menu(menu_id):
    if not isLogged():
        return redirect(url_for('.login'))

    menu_list = MainMenu.query.get(menu_id)
    if not menu_list:
        flash('Пункт не найден', 'error')
        return redirect(url_for('.list_menu'))

    if request.method == "POST":
        title = request.form.get('title')
        url = request.form.get('url')

        if title or url:
            try:
                menu_list.title = title
                menu_list.url = url
                db.session.commit()
                flash("Пункт успешно обновлен", "success")
                return redirect(url_for('.list_menu'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка обновления пункта: {str(e)}", "error")

    return render_template('admin/edit_menu.html', menu=menu, title="Редактировать пункт меню", menu_list=menu_list)