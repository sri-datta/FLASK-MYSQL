from config import mysql

# Add a new user
def add_user(username, password, role):
    query = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
    cursor = mysql.connection.cursor()
    cursor.execute(query, (username, password, role))
    mysql.connection.commit()
    cursor.close()
