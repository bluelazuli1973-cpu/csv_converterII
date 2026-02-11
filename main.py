from app import create_app

app = create_app('development')

print("Application initiated")

if __name__ == "__main__":
    # Match your test_main.http (port 8000)
    app.run(host="127.0.0.1", port=8000, debug=True)