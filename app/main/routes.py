# app/main/routes.py
from . import main_bp

@main_bp.get("/")
def root():
    return {"message": "Hello World"}

@main_bp.get("/hello/<name>")
def say_hello(name: str):
    return {"message": f"Hello {name}"}
