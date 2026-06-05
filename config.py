import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'kirana.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://dbRurik:Rutik123@cluster0.dfeobzy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
