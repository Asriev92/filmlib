from datetime import datetime
from models.database import db


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    film_id = db.Column(db.Integer, db.ForeignKey('films.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'film_id': self.film_id,
            'user': self.author.username if self.author else None,
            'rating': self.rating,
            'text': self.text,
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Review film={self.film_id} user={self.user_id} rating={self.rating}>'
