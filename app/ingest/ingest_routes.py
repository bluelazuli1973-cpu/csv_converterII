from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Upload, Transaction
from .services import parse_csv_to_dataframe

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.get("/")
def home():
    return redirect(url_for("ingest.upload"))


@ingest_bp.get("/upload")
@login_required
def upload():
    return render_template("ingest/upload.html")


@ingest_bp.post("/upload")
@login_required
def upload_post():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please choose a CSV file to upload.", "error")
        return redirect(url_for("ingest.upload"))

    if not file.filename.lower().endswith(".csv"):
        flash("Only .csv files are allowed.", "error")
        return redirect(url_for("ingest.upload"))

    try:
        df = parse_csv_to_dataframe(file)
    except Exception as e:
        flash(f"Upload failed: {e}", "error")
        return redirect(url_for("ingest.upload"))

    upload_row = Upload(
        original_filename=file.filename,
        user_id=current_user.id,
        row_count=int(len(df)),
    )
    db.session.add(upload_row)
    db.session.flush()  # get upload_row.id

    txs = []
    for _, r in df.iterrows():
        txs.append(
            Transaction(
                row_number=int(r["Radnummer"]),
                clearing_number=str(r["Clearingnummer"]).strip(),
                account_number=str(r["Kontonummer"]).strip(),
                product=str(r["Produkt"]).strip() if str(r["Produkt"]).strip() != "" else None,
                currency=str(r["Valuta"]).strip() if str(r["Valuta"]).strip() != "" else None,
                booking_day=r["Bokföringsdag"],
                transaction_day=r["Transaktionsdag"],
                value_day=r["Valutadag"],
                reference=str(r["Referens"]).strip() if str(r["Referens"]).strip() != "" else None,
                description=str(r["Beskrivning"]).strip() if str(r["Beskrivning"]).strip() != "" else None,
                amount=float(r["Belopp"]),
                booked_balance=float(r["Bokfört saldo"]) if r["Bokfört saldo"] is not None else None,
                upload_id=upload_row.id,
            )
        )

    db.session.add_all(txs)
    db.session.commit()

    flash(f"Uploaded {len(txs)} rows from {file.filename}", "success")
    return redirect(url_for("ingest.uploads"))


@ingest_bp.get("/uploads")
@login_required
def uploads():
    uploads_list = (
        db.session.execute(
            db.select(Upload).where(Upload.user_id == current_user.id).order_by(Upload.uploaded_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template("ingest/uploads.html", uploads=uploads_list)
