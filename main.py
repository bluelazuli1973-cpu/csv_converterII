from app import create_app

app = create_app()


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/hello/<name>")
def say_hello(name: str):
    return {"message": f"Hello {name}"}


print("Application initiated")

if __name__ == "__main__":
    # Match your test_main.http (port 8000)
    app.run(host="127.0.0.1", port=8000, debug=True)