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
            return Transaction.transaction_day.type.python_type.fromisoformat(raw)
        except Exception:
            return None

    selected_category = (request.args.get("category") or "").strip()
    start_date = _parse_date_arg("start")
    end_date = _parse_date_arg("end")

    category_expr = db.func.coalesce(Transaction.category, "Uncategorized")
    category_norm = db.func.lower(db.func.trim(category_expr))

    # --- Ensure all template variables are defined on every path ---
    per_day_rows = []
    chart_labels = []
    chart_values = []
    category_labels = []
    category_values = []
    top_category = ""

    # Categories for dropdown (unfiltered so you can always switch)
    # NOTE: Never include financial transactions in this view.
    categories = db.session.execute(
        db.select(category_expr.label("category"))
        .where(
            Transaction.transaction_day.isnot(None),
            Transaction.is_financial_transaction.is_(False),
        )
        .group_by(category_expr)
        .order_by(category_norm.asc())
    ).scalars().all()

    # ... existing code ...

    # Transactions list for table (category + date-range filters)
    # NOTE: Never include financial transactions in this view.
    tx_filters = [
        Transaction.transaction_day.isnot(None),
        Transaction.is_financial_transaction.is_(False),
    ]
    if start_date is not None:
        tx_filters.append(Transaction.transaction_day >= start_date)
    if end_date is not None:
        tx_filters.append(Transaction.transaction_day <= end_date)
    if selected_category:
        tx_filters.append(category_expr == selected_category)

    # Per-day totals for trend (expenses only; displayed as positive)
    per_day_rows = db.session.execute(
        db.select(
            Transaction.transaction_day.label("day"),
            db.func.coalesce(db.func.sum(-Transaction.amount), 0.0).label("total"),
        )
        .where(
            *tx_filters,
            Transaction.is_expense.is_(True),
        )
        .group_by(Transaction.transaction_day)
        .order_by(Transaction.transaction_day.asc())
    ).all()

    chart_labels = [row.day.isoformat() if row.day else "" for row in per_day_rows]
    chart_values = [float(row.total or 0.0) for row in per_day_rows]

    # Category breakdown (base + date filters; intentionally ignore selected_category)
    breakdown_filters = [
        Transaction.transaction_day.isnot(None),
        Transaction.is_financial_transaction.is_(False),
    ]
    if start_date is not None:
        breakdown_filters.append(Transaction.transaction_day >= start_date)
    if end_date is not None:
        breakdown_filters.append(Transaction.transaction_day <= end_date)

    cat_rows = db.session.execute(
        db.select(
            category_expr.label("category"),
            db.func.coalesce(db.func.sum(-Transaction.amount), 0.0).label("total"),
        )
        .where(
            *breakdown_filters,
            Transaction.is_expense.is_(True),
        )
        .group_by(category_expr, category_norm)
        .order_by(
            db.func.coalesce(db.func.sum(-Transaction.amount), 0.0).desc(),
            category_norm.asc(),
        )
    ).all()

    category_labels = [row.category for row in cat_rows]
    category_values = [float(row.total or 0.0) for row in cat_rows]

    # Top category name (first row after ordering by total desc)
    top_category = (cat_rows[0].category if cat_rows else "") or ""

    # Total spending should follow the same filters as the table,
    # but only count expenses and display as positive.
    total_spending = db.session.execute(
        db.select(db.func.coalesce(db.func.sum(-Transaction.amount), 0.0))
        .where(
            *tx_filters,
            Transaction.is_expense.is_(True),
        )
    ).scalar_one()

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

    # ... existing code ...

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
        total_spending=float(total_spending or 0.0),
        top_category=top_category,
    )