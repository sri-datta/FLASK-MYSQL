from flask import Flask, request, jsonify
from config import init_db, mysql
from models import add_user
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'
jwt = JWTManager(app)

# Initialize the database
init_db(app)

# User registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    add_user(username, password, role)
    return jsonify({'message': 'User registered successfully'}), 201

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    cursor = mysql.connection.cursor()
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()

    if user:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify(message="Invalid credentials"), 401


@app.route('/movies', methods=['POST'])
@jwt_required()
def add_movie():
    # Verify the JWT token and get the identity
    current_user = get_jwt_identity()

    # Query the user role from the database using the username from the JWT token
    cursor = mysql.connection.cursor()
    query = "SELECT role FROM users WHERE username = %s"
    cursor.execute(query, (current_user,))
    user = cursor.fetchone()

    if not user or user['role'] != 'admin':
        return jsonify({"message": "Admins only!"}), 403  # Forbidden

    # Get movie details from the request body
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')

    try:
        # Insert movie into the database
        query = "INSERT INTO movies (title, description) VALUES (%s, %s)"
        cursor.execute(query, (title, description))
        mysql.connection.commit()
        return jsonify({"message": "Movie added successfully!"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to add movie"}), 500

@app.route('/ratings', methods=['POST'])
@jwt_required()
def submit_rating():
    current_user = get_jwt_identity()

    # Get the movie_id and rating from the request body
    data = request.get_json()
    movie_id = data.get('movie_id')
    rating = data.get('rating')

    # Check if the movie exists in the database
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    movie = cursor.fetchone()

    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    # Insert the rating into the ratings table
    try:
        query = "INSERT INTO ratings (username, movie_id, rating) VALUES (%s, %s, %s)"
        cursor.execute(query, (current_user, movie_id, rating))
        mysql.connection.commit()
        return jsonify({"message": "Rating submitted successfully!"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to submit rating"}), 500




if __name__ == '__main__':
    app.run(debug=True)
