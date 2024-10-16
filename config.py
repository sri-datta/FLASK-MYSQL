from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'Datta@14'
    app.config['MYSQL_DB'] = 'movie_ratings'  # Corrected key
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    mysql.init_app(app)
