from src import app, db
from flask import render_template

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    return render_template('auth/login.html')

@app.route("/register")
def register():
    return render_template('auth/register.html')


@app.route("/health-check")
def health_check():
    return "Server is running"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)
        