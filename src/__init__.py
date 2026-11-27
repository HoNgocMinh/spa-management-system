import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:root@localhost/spadb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['PAGE_SIZE'] = 20

db = SQLAlchemy(app=app)

from src.models import models
from src.routes import main
from src.routes import auth
from src.routes import dichVu
from src.routes import datLich
