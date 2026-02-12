from flask import redirect, url_for
from flask_login import current_user

from . import main_bp


@main_bp.get("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("analytics.trend"))
    return redirect(url_for("auth.login"))


@main_bp.get("/hello/<name>")
def say_hello(name: str):
    return {"message": f"Hello {name}"}