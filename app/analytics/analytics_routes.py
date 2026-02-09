from flask import Blueprint, render_template
from flask_login import login_required

from ..extensions import db
from ..models import DataPoint

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/trend")
@login_required
def trend():
    # Total value per day (across all metrics)
    rows = db.session.execute(
        db.select(DataPoint.day, db.func.sum(DataPoint.value).label("total"))
        .group_by(DataPoint.day)
        .order_by(DataPoint.day.asc())
    ).all()

    # Also totals by metric (overall)
    metrics = db.session.execute(
        db.select(DataPoint.metric, db.func.sum(DataPoint.value).label("total"))
        .group_by(DataPoint.metric)
        .order_by(db.func.sum(DataPoint.value).desc())
    ).all()

    return render_template("analytics/trend.html", per_day=rows, per_metric=metrics)
