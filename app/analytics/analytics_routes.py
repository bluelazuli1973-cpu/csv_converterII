from flask import Blueprint, render_template
from flask_login import login_required

from ..extensions import db
from ..models import Transaction

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/trend")
@login_required
def trend():
    # Total value per day (across all metrics)
    rows = db.session.execute(
        db.select(Transaction.day, db.func.sum(Transaction.value).label("total"))
        .group_by(Transaction.day)
        .order_by(Transaction.day.asc())
    ).all()

    # Also totals by metric (overall)
    metrics = db.session.execute(
        db.select(Transaction.metric, db.func.sum(Transaction.value).label("total"))
        .group_by(Transaction.metric)
        .order_by(db.func.sum(Transaction.value).desc())
    ).all()

    return render_template("analytics/trend.html", per_day=rows, per_metric=metrics)
