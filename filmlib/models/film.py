from datetime import datetime
from models.database import db


class Genre(db.Model):
    __tablename__ = 'genres'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    films = db.relationship('Film', backref='genre', lazy='dynamic')

    def __repr__(self):
        return f'<Genre {self.name}>'


class Film(db.Model):
    __tablename__ = 'films'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    director = db.Column(db.String(150), default='')
    description = db.Column(db.Text, default='')
    poster = db.Column(db.String(256), default='default_poster.jpg')
    genre_id = db.Column(db.Integer, db.ForeignKey('genres.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship('Review', backref='film', lazy='dynamic',
                              cascade='all, delete-orphan')

    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def to_dict(self, full=False):
        data = {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'director': self.director,
            'genre': self.genre.name if self.genre else None,
            'genre_id': self.genre_id,
            'poster_url': f'/static/uploads/{self.poster}',
            'rating': self.average_rating(),
            'reviews_count': self.reviews.count(),
            'added_by': self.author.username if self.author else None,
            'created_at': self.created_at.isoformat(),
        }
        if full:
            data['description'] = self.description
            data['reviews'] = [r.to_dict() for r in
                                self.reviews.order_by('created_at').all()]
        return data

    def __repr__(self):
        return f'<Film {self.title} ({self.year})>'
