from flask import Blueprint, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models import Transaction

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/trend")
@login_required
def trend():
    def _parse_date_arg(name: str):
        raw = (request.args.get(name) or "").strip()
        if not raw:
            return None
        try:
            # expects YYYY-MM-DD from <input type="date">
            return Transaction.transaction_day.type.python_type.fromisoformat(raw)
        except Exception:
            return None

    selected_category = (request.args.get("category") or "").strip()
    start_date = _parse_date_arg("start")
    end_date = _parse_date_arg("end")

    # Base filters (apply to charts; category filter is for tx table only)
    base_filters = [
        Transaction.transaction_day.isnot(None),
        Transaction.is_expense.is_(True),
    ]
    if start_date is not None:
        base_filters.append(Transaction.transaction_day >= start_date)
    if end_date is not None:
        base_filters.append(Transaction.transaction_day <= end_date)

    # Daily totals over transaction date (display spending as positive)
    per_day_rows = db.session.execute(
        db.select(
            Transaction.transaction_day,
            db.func.sum(-Transaction.amount).label("total"),
        )
        .where(*base_filters)
        .group_by(Transaction.transaction_day)
        .order_by(Transaction.transaction_day.asc())
    ).all()

    # Spending by category (expenses only), display spending as positive
    category_expr = db.func.coalesce(Transaction.category, "Uncategorized")
    category_norm = db.func.lower(db.func.trim(category_expr))

    per_category_rows = db.session.execute(
        db.select(
            category_expr.label("category"),
            db.func.sum(-Transaction.amount).label("total"),
        )
        .where(
            *base_filters,
            category_norm != "övrigt/okänd",
        )
        .group_by(category_expr)
        .order_by(db.func.sum(-Transaction.amount).desc())
        .limit(5)
    ).all()

    # Categories list for filter dropdown
    categories = [
        row[0]
        for row in db.session.execute(
            db.select(category_expr.label("category"))
            .where(Transaction.category.isnot(None))
            .group_by(category_expr)
            .order_by(category_expr.asc())
        ).all()
        if row[0]
    ]

    # Transactions list for table (category + date-range filters)
    tx_filters = [Transaction.transaction_day.isnot(None)]
    if start_date is not None:
        tx_filters.append(Transaction.transaction_day >= start_date)
    if end_date is not None:
        tx_filters.append(Transaction.transaction_day <= end_date)
    if selected_category:
        tx_filters.append(category_expr == selected_category)

    tx_rows = db.session.execute(
        db.select(
            Transaction.transaction_day,
            Transaction.place_purchase,
            Transaction.category,
            Transaction.amount,
        )
        .where(*tx_filters)
        .order_by(Transaction.transaction_day.asc(), Transaction.id.asc())
    ).all()

    # Chart.js likes plain lists
    chart_labels = [d.isoformat() for d, _total in per_day_rows]
    chart_values = [float(total or 0.0) for _d, total in per_day_rows]

    category_labels = [str(cat) for cat, _total in per_category_rows]
    category_values = [float(total or 0.0) for _cat, total in per_category_rows]

    return render_template(
        "analytics/trend.html",
        per_day=per_day_rows,
        tx_rows=tx_rows,
        chart_labels=chart_labels,
        chart_values=chart_values,
        category_labels=category_labels,
        category_values=category_values,
        categories=categories,
        selected_category=selected_category,
        start_date=start_date.isoformat() if start_date else "",
        end_date=end_date.isoformat() if end_date else "",
    )