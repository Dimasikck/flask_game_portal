import shutil
import zipfile
from flask import Blueprint, render_template, url_for, redirect, session, request, flash, g
from werkzeug.utils import secure_filename
import os
from db import db, Posts, Users, Games, MainMenu,Comments, CommentLikes
from datetime import datetime, timedelta
from sqlalchemy import func, asc, desc
from git import Repo
import hmac
import hashlib

#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут ДЛЯ ПОЛУЧЕНИЯ И ОТОБРАЖЕНИЯ АВТАРА ПОЛЬЗОВАТЕЛЯ 
"""
#-----------------------------------------------------------------------------------------------------------------
admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

menu = [{'url': '.index', 'title': 'Панель'},
        {'url': '.list_users', 'title': 'Список пользователей'},
        {'url': '.list_games', 'title': 'Список игр'},
        {'url': '.list_menu', 'title': 'Пункты меню'},
        {'url': '.logout', 'title': 'Выйти'}]

SECRET_KEY = '43fswQtodqAAAAAaLYQVnaNOyAwmqeOqWsGPvweqe'

GENRES = ['🔫Экшн', '🌏Приключения', '🧙‍♂️RPG', '📈Стратегия', '💼Симулятор', '⚽Спорт', '🗿Головоломка', '🏃‍♂️Платформер', 'Другое']
def isLogged():
    return True if session.get('admin_logged') else False
def login_admin():
    session['admin_logged'] = 1
def logout_admin():
    session.pop('admin_logged', None)
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Основной маршрут (Главная страница) Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------
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
            func.date(func.datetime(Users.time, 'unixepoch')),  # Преобразуем Unix timestamp в дату
            func.count()
        )
        .filter(Users.time >= int(last_week.timestamp()))
        .group_by(func.date(func.datetime(Users.time, 'unixepoch')))
        .all()
    )
    game_stats = (
        db.session.query(
            func.date(func.datetime(Games.time, 'unixepoch')),  # То же для Games
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

#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для обновления сайта через админ-панель
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/update_site', methods=['POST'])
def update_site():
    if not isLogged():
        return redirect(url_for('.login'))

    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    try:
        print("Pulling from Git")
        repo = Repo('/home/Dimasickc/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')  # Принудительно синхронизируем с origin/main
        print("Git pull successful")
        os.system('touch /var/www/dimasickc_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        flash("Сайт успешно обновлен", "success")
    except Exception as e:
        print(f"Error: {str(e)}")
        flash(f"Ошибка обновления сайта: {str(e)}", "error")

    return redirect(url_for('.index'))

#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для обновления сайта через вебхук GitHub
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/webhook', methods=['POST'])
def webhook():
    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    signature = request.headers.get('X-Hub-Signature-256')
    print(f"Signature: {signature}")
    if not signature:  # Если подписи нет, это не запрос от GitHub
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
        repo = Repo('/home/Dimasickc/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')  # Принудительно синхронизируем с origin/main
        print("Git pull successful")
        os.system('touch /var/www/dimasickc_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        return 'Updated successfully', 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут страницы АВТОРИЗАЦИИ для Панели администратора
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/login', methods=["POST", "GET"])
def login():
    if isLogged():
        return redirect(url_for('.index'))

    if request.method == "POST":
        if request.form['user'] == "admin" and request.form['psw'] == "12345":
            login_admin()
            return redirect(url_for('.index'))
        else:
            flash("Неверная пара логин/пароль", "error")

    return render_template('admin/login.html', title='Админ-панель')
#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для ВЫХОДА из авторизации  Панели администратора
"""
#-----------------------------------------------------------------------------------------------------------------

@admin.route('/logout', methods=["POST", "GET"])
def logout():
    if not isLogged():
        return redirect(url_for('.login'))

    logout_admin()

    return redirect(url_for('.login'))
#-----------------------------------------------------------------------------------------------------------------
"""
                            Маршрут страницы списка постов на Панели администратора 
"""
#-----------------------------------------------------------------------------------------------------------------

@admin.route('/list_pubs')
def list_pubs():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        list = Posts.query.all()
    except Exception as e:
        flash(f'Оштбка получения статей: {str(e)}', 'error')
        list = []
    return render_template('admin/list_pubs.html', title='Список статей', menu=menu, list=list)

#-----------------------------------------------------------------------------------------------------------------
"""
                            Маршрут страницы СПИСКА ПОЛЬЗОВАТЕЛЕЙ в Панели администратора 
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/list_users')
def list_users():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        # Получаем параметры запроса
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')  # По умолчанию сортировка по дате убывания
        filter_role = request.args.get('role', '')  # Фильтр по роли (если есть в модели Users)
        # Базовый запрос
        query = Users.query
        # Поиск по логину, имени или email
        if search:
            query = query.filter(
                (Users.login.ilike(f'%{search}%')) |
                (Users.name.ilike(f'%{search}%')) |
                (Users.email.ilike(f'%{search}%'))
            )
        # Фильтрация по роли (предполагаем, что есть поле role, если нет — убрать этот блок)
        if filter_role:
            query = query.filter(Users.role == filter_role)
        # Сортировка
        if sort == 'login_asc':
            query = query.order_by(asc(Users.login))
        elif sort == 'login_desc':
            query = query.order_by(desc(Users.login))
        elif sort == 'time_asc':
            query = query.order_by(asc(Users.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Users.time))
        else:
            query = query.order_by(desc(Users.time))  # По умолчанию
        users = query.all()
    except Exception as e:
        flash(f'Ошибка получения пользователей: {str(e)}', 'error')
        users = []

    return render_template('admin/list_users.html', title='Список пользователей', menu=menu, list=users,
                          search=search, sort=sort, filter_role=filter_role)

#-----------------------------------------------------------------------------------------------------------------
"""
                              Маршрут страницы  СПИСКА ИГР в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/list_games')
def list_games():
    if not isLogged():
        return redirect(url_for('.login'))

    try:
        # Получаем параметры запроса
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')  # По умолчанию сортировка по дате убывания
        filter_type = request.args.get('type', '')  # Фильтр по типу игры (link или pygame)
        filter_genre = request.args.get('genre', '')# Фильтр по жанру
        # Базовый запрос
        query = Games.query
        # Поиск по названию или описанию
        if search:
            query = query.filter(
                (Games.title.ilike(f'%{search}%')) |
                (Games.description.ilike(f'%{search}%'))
            )
        # Фильтрация по типу игры
        if filter_type == 'link':
            query = query.filter(Games.link.like('http%'))
        elif filter_type == 'pygame':
            query = query.filter(Games.link.like('%'))
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

    return render_template('admin/list_games.html', title='Список игр', menu=menu, games=games,
                          search=search, sort=sort, filter_type=filter_type, filter_genre=filter_genre, genres=GENRES)
#-----------------------------------------------------------------------------------------------------------------
"""
                        Маршрут страницы СПИСКА ПУНКТОВ МЕНЮ САЙТА в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------

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
#-----------------------------------------------------------------------------------------------------------------
"""
                        Маршрут страницы ДОБАВЛЕНИЯ ПУНКТА МЕНЮ ДЛЯ САЙТА в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------
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
                flash('Пукт успешно добавлена', 'success')
                return redirect(url_for('.list_menu'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления пункта: {str(e)}', 'error')
    return render_template('admin/add_menu.html', menu=menu, title='Добавить пункт меню')

# -----------------------------------------------------------------------------------------------------------------
# Маршрут добавления игры
# -----------------------------------------------------------------------------------------------------------------
@admin.route('/add_game', methods=['POST', 'GET'])
def add_game():
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        genre = request.form.get('genre')
        game_type = request.form.get('game_type')
        cover_file = request.files.get('cover')

        if not title or not description or not cover_file:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                if Games.query.filter_by(title=title).first():
                    flash('Игра с таким названием уже добавлена', 'error')
                    return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                cover_data = cover_file.read()
                new_game = Games(title=title, description=description, cover=cover_data, genre=genre)

                if game_type == 'link':
                    link = request.form.get('link')
                    if not link:
                        flash('Ссылка для внешней игры обязательна', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                    if Games.query.filter_by(link=link).first():
                        flash('Игра с такой ссылкой уже добавлена', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)
                    new_game.link = link
                    new_game.game_type = 'link'
                elif game_type == 'pygame':
                    pygame_zip = request.files.get('pygame_zip')
                    pygame_installer = request.files.get('pygame_installer')
                    pygame_screenshots_zip = request.files.get('pygame_screenshots_zip')
                    if not pygame_zip:
                        flash('Необходимо загрузить архив с игрой', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)

                    # Создаем папку с именем игры
                    game_folder = secure_filename(pygame_zip.filename).rsplit('.', 1)[0]
                    # game_path = os.path.join('static/games', game_folder)
                    game_path = os.path.join('flask_game_portal/static/games', game_folder)
                    os.makedirs(game_path, exist_ok=True)

                    # Сохранение и разархивирование архива игры с сохранением структуры
                    game_zip_path = os.path.join(game_path, 'pygame.zip')
                    pygame_zip.save(game_zip_path)
                    with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(game_path)  # Извлекаем все с исходной структурой
                    os.remove(game_zip_path)

                    # Сохранение и разархивирование скриншотов с сохранением структуры
                    if pygame_screenshots_zip:
                        pygame_screenshots_path = os.path.join(game_path, 'screenshots')
                        os.makedirs(pygame_screenshots_path, exist_ok=True)
                        screenshots_zip_path = os.path.join(pygame_screenshots_path, 'screenshots.zip')
                        pygame_screenshots_zip.save(screenshots_zip_path)
                        with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(pygame_screenshots_path)  # Извлекаем все с исходной структурой
                        os.remove(screenshots_zip_path)
                    if pygame_installer:
                        installer_path = os.path.join(game_path, f"{game_folder}.exe")
                        pygame_installer.save(installer_path)
                        new_game.installer = installer_path
                    new_game.link = game_folder
                    new_game.game_type = 'pygame'

                elif game_type == 'unity':
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
                    game_zip_path = os.path.join(game_path, 'unity_game.zip')
                    unity_zip.save(game_zip_path)
                    with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(game_path)
                    os.remove(game_zip_path)
                    # Сохранение и разархивирование скриншотов с сохранением структуры
                    if unity_screenshots_zip:
                        unity_screenshots_path = os.path.join(game_path, 'screenshots')
                        os.makedirs(unity_screenshots_path, exist_ok=True)
                        screenshots_zip_path = os.path.join(unity_screenshots_path, 'screenshots.zip')
                        unity_screenshots_zip.save(screenshots_zip_path)
                        with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(unity_screenshots_path)  # Извлекаем все с исходной структурой
                        os.remove(screenshots_zip_path)
                    if unity_installer:
                        installer_path = os.path.join(game_path, f"{game_folder}.exe")
                        unity_installer.save(installer_path)
                        new_game.installer = installer_path
                    new_game.link = game_folder
                    new_game.game_type = 'unity'

                db.session.add(new_game)
                db.session.commit()
                flash('Игра успешно добавлена', 'success')
                return redirect(url_for('.list_games'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления игры: {str(e)}', 'error')
    return render_template('admin/add_game.html', menu=menu, title='Добавить игру', genres=GENRES)


# -----------------------------------------------------------------------------------------------------------------
"""
                         Маршрут для РЕДАКТИРОВАНИЯ ИГРЫ в Панели администратора  
"""


# -----------------------------------------------------------------------------------------------------------------
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
        game_type = request.form.get('game_type')
        cover_file = request.files.get('cover')

        if title or description or (cover_file and cover_file.filename):
            if title and description:
                try:
                    # Проверяем, что игра с таким названием не существует (кроме текущей)
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

                    if game_type == 'link':
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
                        game.game_type = game_type

                    elif game_type == 'pygame':
                        pygame_zip = request.files.get('pygame_zip')
                        pygame_installer = request.files.get('pygame_installer')
                        pygame_screenshots_zip = request.files.get('pygame_screenshots_zip')
                        if pygame_zip:  # Обновляем только если загружен новый архив
                            # Удаляем старую папку игры, если она существует
                            old_game_folder = game.link
                            if old_game_folder and os.path.exists(os.path.join('flask_game_portal/static/games', old_game_folder)):
                                shutil.rmtree(os.path.join('flask_game_portal/static/games', old_game_folder))
                            # if old_game_folder and os.path.exists(os.path.join('static/games', old_game_folder)):
                            #     shutil.rmtree(os.path.join('static/games', old_game_folder))

                            # Создаем новую папку с именем игры
                            game_folder = secure_filename(pygame_zip.filename).rsplit('.', 1)[0]
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            # game_path = os.path.join('static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)

                            # Сохранение и разархивирование архива игры с сохранением структуры
                            pygame_zip_path = os.path.join(game_path, 'pygame.zip')
                            pygame_zip.save(pygame_zip_path)
                            with zipfile.ZipFile(pygame_zip_path, 'r') as zip_ref:
                                zip_ref.extractall(game_path)  # Извлекаем все с исходной структурой
                            os.remove(pygame_zip_path)

                            # Сохранение и разархивирование скриншотов с сохранением структуры
                            if pygame_screenshots_zip:
                                screenshots_path = os.path.join(game_path, 'screenshots')
                                os.makedirs(screenshots_path, exist_ok=True)
                                screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                                pygame_screenshots_zip.save(screenshots_zip_path)
                                with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(screenshots_path)  # Извлекаем все с исходной структурой
                                os.remove(screenshots_zip_path)
                            game.link = game_folder
                        if pygame_installer:
                            game_folder = game.link if game.link else secure_filename(title)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            # game_path = os.path.join('static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)
                            installer_path = os.path.join(game_path, f"{game_folder}.exe")
                            if game.installer and os.path.exists(game.installer):
                                os.remove(game.installer)
                            pygame_installer.save(installer_path)
                            game.installer = installer_path
                        game.game_type = game_type

                    elif game_type == 'unity' and request.files.get('unity.zip'):
                        unity_zip = request.files.get('unity_zip')
                        unity_installer = request.files.get('unity_installer')
                        unity_screenshots_zip = request.files.get('unity_screenshots_zip')
                        if unity_installer:  # Обновляем только если загружен новый архив
                            # Удаляем старую папку игры, если она существует
                            old_game_folder = game.link
                            if old_game_folder and os.path.exists(os.path.join('flask_game_portal/static/games', old_game_folder)):
                                shutil.rmtree(os.path.join('flask_game_portal/static/games', old_game_folder))
                            # if old_game_folder and os.path.exists(os.path.join('static/games', old_game_folder)):
                            #     shutil.rmtree(os.path.join('static/games', old_game_folder))

                            # Создаем новую папку с именем игры
                            game_folder = secure_filename(unity_zip.filename).rsplit('.', 1)[0]
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)

                            # Сохранение и разархивирование архива игры с сохранением структуры
                            unity_game_zip_path = os.path.join(game_path, 'game.zip')
                            unity_zip.save(unity_game_zip_path)
                            with zipfile.ZipFile(unity_game_zip_path, 'r') as zip_ref:
                                zip_ref.extractall(game_path)  # Извлекаем все с исходной структурой
                            os.remove(unity_game_zip_path)

                            # Сохранение и разархивирование скриншотов с сохранением структуры
                            if unity_screenshots_zip:
                                screenshots_path = os.path.join(game_path, 'screenshots')
                                os.makedirs(screenshots_path, exist_ok=True)
                                screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                                unity_screenshots_zip.save(screenshots_zip_path)
                                with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(screenshots_path)  # Извлекаем все с исходной структурой
                                os.remove(screenshots_zip_path)
                            game.link = game_folder
                        if unity_installer:
                            game_folder = secure_filename(title)
                            # game_path = os.path.join('static/games', game_folder)
                            game_path = os.path.join('flask_game_portal/static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)
                            installer_path = os.path.join(game_path, f"{game_folder}.exe")
                            if game.installer and os.path.exists(game.installer):
                                os.remove(game.installer)
                            unity_installer.save(installer_path)
                            game.installer = installer_path
                        game.game_type = game_type

                    db.session.commit()
                    flash("Игра успешно обновлена", "success")
                    return redirect(url_for('.list_games'))
                except Exception as e:
                    db.session.rollback()
                    flash(f"Ошибка обновления игры: {str(e)}", "error")
            else:
                flash("Все поля должны быть заполнены", "error")

    return render_template('admin/edit_game.html', menu=menu, title="Редактировать игру", game=game, genres=GENRES)
#-----------------------------------------------------------------------------------------------------------------
"""
                       Маршрут  для УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЯ в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/delete_user/<int:user_id>', methods=['POST', "GET"])
def delete_user(user_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        user = Users.query.get(user_id)
        if user:
            # Удаляем все комментарии пользователя
            Comments.query.filter_by(user_id=user.id).delete()
            # Удаляем все лайки пользователя
            CommentLikes.query.filter_by(user_id=user.id).delete()
            # Удаляем самого пользователя
            db.session.delete(user)
            db.session.commit()
            flash('Пользователь успешно удален', 'success')
        else:
            flash('Ошибка удаления пользователя', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления пользователя: {str(e)}', 'error')
    return redirect(url_for('.list_users'))
#-----------------------------------------------------------------------------------------------------------------
"""
                            Маршрут  для УДАЛЕНИЯ ИГРЫ в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------

@admin.route('/delete-game/<int:game_id>', methods=['POST', "GET"])
def delete_game(game_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        game = Games.query.get(game_id)
        if game:
            # Проверяем, является ли игра Pygame (нет http в начале link)
            if game.link and game.game_type != 'link':
                game_folder = game.link.replace('flask_game_portal/static/games/', '')  # Извлекаем имя папки из пути
                game_path = os.path.join('flask_game_portal/static/games', game_folder)
                # game_folder = game.link.replace('static/games/', '')  # Извлекаем имя папки из пути
                # game_path = os.path.join('static/games', game_folder)
                if os.path.exists(game_path):
                    shutil.rmtree(game_path)  # Удаляем папку с игрой и всем содержимым
                    flash(f'Папка игры {game_folder} удалена', 'success')
                else:
                    flash(f'Папка игры {game_folder} не найдена', 'error')

            db.session.delete(game)
            db.session.commit()
            flash('Игра успешно удалена', 'success')
        else:
            flash('Игра не найдена', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления игры: {str(e)}', 'error')
    return redirect(url_for('.list_games'))
#-----------------------------------------------------------------------------------------------------------------
"""
                       Маршрут  для УДАЛЕНИЯ ПУКТА МЕНЮ в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------

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
#-----------------------------------------------------------------------------------------------------------------
"""
                            Маршрут для РЕДАКТИРОВАНИЯ ПУНКТА МЕНЮ в Панели администратора  
"""
#-----------------------------------------------------------------------------------------------------------------

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

        # Проверяем, что хотя бы одно поле формы заполнено, иначе считаем, что форму не отправили
        if title or url:
            try:
                menu_list.title = title
                menu_list.url = url
                db.session.commit()
                flash("Пункт успешно обновлена", "success")
                return redirect(url_for('.list_menu'))  # Перенаправление на список игр
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка обновления пункта: {str(e)}", "error")


    return render_template('admin/edit_menu.html', menu=menu, title="Редактировать пункт меню", menu_list=menu_list)
