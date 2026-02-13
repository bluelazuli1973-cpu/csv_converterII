from app import create_app

app = create_app('development')

print("Application initiated")

def _ensure_ai_models_ready() -> None:
    """
    Make sure the category model exists at app startup.
    If it doesn't, generate training data and train a model.
    """
    from app.ai_agent_models import ensure_category_model
    ensure_category_model()

try:
    _ensure_ai_models_ready()
    print("Category model ready.")
except Exception as e:
    # Don't prevent the web server from starting; surface the error clearly.
    # If you prefer "fail fast" instead, remove this try/except.
    print("Warning: failed to ensure category model at startup.")
    print(f"Reason: {e!r}")

if __name__ == "__main__":
    # Match your test_main.http (port 8000)
    app.run(host="127.0.0.1", port=8000, debug=True)