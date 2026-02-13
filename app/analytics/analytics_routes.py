from flask import Blueprint, render_template
from flask_login import login_required

from ..extensions import db
from ..models import Transaction

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/trend")
@login_required
def trend():
    # Daily totals over transaction date
    # display spending as positive
    per_day_rows = db.session.execute(
        db.select(
            Transaction.transaction_day,
            db.func.sum(-Transaction.amount).label("total"),
        )
        .where(
            Transaction.transaction_day.isnot(None),
            Transaction.is_expense.is_(True),
        )
        .group_by(Transaction.transaction_day)
        .order_by(Transaction.transaction_day.asc())
    ).all()

    # Transactions list for table (includes place of purchase)
    tx_rows = db.session.execute(
        db.select(
            Transaction.transaction_day,
            Transaction.place_purchase,
            Transaction.category,
            Transaction.amount,
        )
        .where(Transaction.transaction_day.isnot(None))
        .order_by(Transaction.transaction_day.asc(), Transaction.id.asc())
    ).all()

    # Chart.js likes plain lists
    chart_labels = [d.isoformat() for d, _total in per_day_rows]
    chart_values = [float(total or 0.0) for _d, total in per_day_rows]

    return render_template(
        "analytics/trend.html",
        per_day=per_day_rows,
        tx_rows=tx_rows,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )