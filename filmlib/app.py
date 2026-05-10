import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models.database import db
from models.user import User
from models.film import Film, Genre
from models.review import Review

# Настройки для PythonAnywhere
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'filmlib-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'filmlib.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 МБ

db.init_app(app)

from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите, чтобы продолжить.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not email or not password:
            flash('Заполните все поля.', 'danger')
        elif password != confirm:
            flash('Пароли не совпадают.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован.', 'danger')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get('remember')))
            flash('Вы вошли!', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    genre_id = request.args.get('genre', type=int)
    page = request.args.get('page', 1, type=int)
    genres = Genre.query.order_by(Genre.name).all()

    films_q = Film.query
    if query:
        films_q = films_q.filter(Film.title.ilike(f'%{query}%'))
    if genre_id:
        films_q = films_q.filter(Film.genre_id == genre_id)

    pagination = films_q.order_by(Film.title).paginate(page=page, per_page=24, error_out=False)
    films = pagination.items

    return render_template('index.html', films=films, genres=genres,
                           query=query, genre_id=genre_id, pagination=pagination)


@app.route('/film/<int:film_id>')
def film_detail(film_id):
    film = Film.query.get_or_404(film_id)
    reviews = Review.query.filter_by(film_id=film_id).order_by(Review.created_at.desc()).all()
    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(film_id=film_id, user_id=current_user.id).first()
    avg = film.average_rating()
    return render_template('film_detail.html', film=film, reviews=reviews,
                           user_review=user_review, avg=avg)


@app.route('/film/add', methods=['GET', 'POST'])
@login_required
def add_film():
    genres = Genre.query.order_by(Genre.name).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        year = request.form.get('year', type=int)
        description = request.form.get('description', '').strip()
        genre_id = request.form.get('genre_id', type=int)
        director = request.form.get('director', '').strip()

        if not title or not year:
            flash('Название и год обязательны.', 'danger')
            return render_template('add_film.html', genres=genres)

        poster_filename = 'default_poster.jpg'
        file = request.files.get('poster')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f'{current_user.id}_{filename}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            poster_filename = unique_name

        film = Film(title=title, year=year, description=description,
                    genre_id=genre_id, director=director,
                    poster=poster_filename, user_id=current_user.id)
        db.session.add(film)
        db.session.commit()
        flash('Фильм добавлен!', 'success')
        return redirect(url_for('film_detail', film_id=film.id))

    return render_template('add_film.html', genres=genres)


@app.route('/film/<int:film_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_film(film_id):
    film = Film.query.get_or_404(film_id)
    if film.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    genres = Genre.query.order_by(Genre.name).all()
    if request.method == 'POST':
        film.title = request.form.get('title', '').strip()
        film.year = request.form.get('year', type=int)
        film.description = request.form.get('description', '').strip()
        film.genre_id = request.form.get('genre_id', type=int)
        film.director = request.form.get('director', '').strip()

        file = request.files.get('poster')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f'{current_user.id}_{filename}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            film.poster = unique_name

        db.session.commit()
        flash('Фильм обновлён!', 'success')
        return redirect(url_for('film_detail', film_id=film.id))

    return render_template('edit_film.html', film=film, genres=genres)


@app.route('/film/<int:film_id>/delete', methods=['POST'])
@login_required
def delete_film(film_id):
    film = Film.query.get_or_404(film_id)
    if film.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(film)
    db.session.commit()
    flash('Фильм удалён.', 'info')
    return redirect(url_for('index'))


@app.route('/film/<int:film_id>/review', methods=['POST'])
@login_required
def add_review(film_id):
    Film.query.get_or_404(film_id)
    existing = Review.query.filter_by(film_id=film_id, user_id=current_user.id).first()
    if existing:
        flash('Вы уже оставили отзыв на этот фильм.', 'warning')
        return redirect(url_for('film_detail', film_id=film_id))
    rating = request.form.get('rating', type=int)
    text = request.form.get('text', '').strip()
    if not rating or rating < 1 or rating > 10:
        flash('Укажите оценку от 1 до 10.', 'danger')
        return redirect(url_for('film_detail', film_id=film_id))
    review = Review(film_id=film_id, user_id=current_user.id, rating=rating, text=text)
    db.session.add(review)
    db.session.commit()
    flash('Отзыв добавлен!', 'success')
    return redirect(url_for('film_detail', film_id=film_id))


@app.route('/profile')
@login_required
def profile():
    films = Film.query.filter_by(user_id=current_user.id).order_by(Film.created_at.desc()).all()
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('profile.html', films=films, reviews=reviews)


@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран.', 'danger')
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f'avatar_{current_user.id}_{filename}'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        current_user.avatar = unique_name
        db.session.commit()
        flash('Аватар обновлен!', 'success')
    else:
        flash('Недопустимый формат файла.', 'danger')
    return redirect(url_for('profile'))


@app.route('/api/films', methods=['GET'])
def api_films():
    q = request.args.get('q', '').strip()
    genre_id = request.args.get('genre_id', type=int)
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = request.args.get('offset', 0, type=int)

    films_q = Film.query
    if q:
        films_q = films_q.filter(Film.title.ilike(f'%{q}%'))
    if genre_id:
        films_q = films_q.filter(Film.genre_id == genre_id)

    total = films_q.count()
    films = films_q.order_by(Film.title).limit(limit).offset(offset).all()
    return jsonify({'total': total, 'limit': limit, 'offset': offset,
                    'films': [f.to_dict() for f in films]})


@app.route('/api/films/<int:film_id>', methods=['GET'])
def api_film(film_id):
    film = Film.query.get_or_404(film_id)
    return jsonify(film.to_dict(full=True))


@app.route('/api/genres', methods=['GET'])
def api_genres():
    genres = Genre.query.order_by(Genre.name).all()
    return jsonify([{'id': g.id, 'name': g.name} for g in genres])


def init_db():
    with app.app_context():
        db.create_all()
        genre_names = ['Боевик', 'Комедия', 'Драма', 'Фантастика',
                       'Ужасы', 'Мелодрама', 'Аниме', 'Документальный',
                       'Триллер', 'Мультфильм']
        if not Genre.query.first():
            for name in genre_names:
                db.session.add(Genre(name=name))
            db.session.commit()


# Инициализация при запуске (для PythonAnywhere)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

if __name__ == '__main__':
    app.run(debug=False)
