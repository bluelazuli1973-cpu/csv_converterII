from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import admin_bp
from ..extensions import db
from ..models import MonthlyBudget


def _parse_month(value: str) -> tuple[int, int] | None:
    """
    Accepts HTML <input type="month"> value: 'YYYY-MM'
    """
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, "%Y-%m")
        return dt.year, dt.month
    except Exception:
        return None


@admin_bp.get("/budget")
@login_required
def budget_get():
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    mb = db.session.execute(
        db.select(MonthlyBudget).where(
            MonthlyBudget.user_id == current_user.id,
            MonthlyBudget.year == year,
            MonthlyBudget.month == month,
        )
    ).scalar_one_or_none()

    # Provide defaults for the form
    selected_month = f"{year:04d}-{month:02d}"
    current_amount = (str(mb.amount) if mb else "")

    recent = db.session.execute(
        db.select(MonthlyBudget)
        .where(MonthlyBudget.user_id == current_user.id)
        .order_by(MonthlyBudget.year.desc(), MonthlyBudget.month.desc())
        .limit(12)
    ).scalars().all()

    return render_template(
        "admin/budget.html",
        selected_month=selected_month,
        current_amount=current_amount,
        recent_budgets=recent,
    )


@admin_bp.post("/budget")
@login_required
def budget_post():
    ym = _parse_month(request.form.get("month", ""))
    amount_raw = (request.form.get("amount") or "").strip()

    if ym is None:
        flash("Please select a valid month.", "error")
        return redirect(url_for("admin.budget_get"))

    year, month = ym

    try:
        amount = Decimal(amount_raw)
    except (InvalidOperation, TypeError):
        flash("Please enter a valid budget amount (e.g. 2500.00).", "error")
        return redirect(url_for("admin.budget_get"))

    if amount < 0:
        flash("Budget amount cannot be negative.", "error")
        return redirect(url_for("admin.budget_get"))

    mb = db.session.execute(
        db.select(MonthlyBudget).where(
            MonthlyBudget.user_id == current_user.id,
            MonthlyBudget.year == year,
            MonthlyBudget.month == month,
        )
    ).scalar_one_or_none()

    if mb is None:
        mb = MonthlyBudget(user_id=current_user.id, year=year, month=month, amount=amount)
        db.session.add(mb)
    else:
        mb.amount = amount

    db.session.commit()
    flash(f"Saved budget for {year:04d}-{month:02d}.", "success")
    return redirect(url_for("admin.budget_get"))
