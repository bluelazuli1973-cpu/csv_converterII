from datetime import datetime, timezone, date

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    uploads = db.relationship("Upload", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class Upload(db.Model):
    __tablename__ = "uploads"
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(512), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    row_count = db.Column(db.Integer, nullable=False, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="uploads")

    transactions = db.relationship("Transaction", back_populates="upload", cascade="all, delete-orphan")




class Transaction(db.Model):
    """
    CSV schema (bank transactions) based on provided header:
    Valuta, Bokningsdag, Transaktionsdag, Valutadag, Plats, Referens, Belopp
    """
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)

    currency = db.Column(db.String(8), nullable=True, index=True)           # Currency

    booking_day = db.Column(db.Date, nullable=True, index=True)             # Bokföringsdag
    transaction_day = db.Column(db.Date, nullable=True, index=True)         # Transaktionsdag
    currency_day = db.Column(db.Date, nullable=True, index=True)            # Valutadag day of currency conversion

    place_purchase = db.Column(db.String(256), nullable=True, index=True)    #Place of purchase
    description = db.Column(db.String(512), nullable=True)                   #Reference

    amount = db.Column(db.Float, nullable=False)                               # Belopp (can be +/-)

    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id"), nullable=False, index=True)
    upload = db.relationship("Upload", back_populates="transactions")