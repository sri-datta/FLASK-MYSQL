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
    role = data.get('role')

    # Validate the role - only "admin" or "user" allowed
    if role not in ["admin", "user"]:
        return jsonify({"message": "Invalid role. Only 'admin' or 'user' are allowed."}), 400

    try:
        # Register the new user with the provided role
        add_user(username, password, role)
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'Failed to register user'}), 500
    

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

    # Get the user role from the database using the username from the JWT token
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE username = %s", (current_user,))
    user = cursor.fetchone()

    if not user or user['role'] == 'admin':
        return jsonify({"message": "Admins are not allowed to submit ratings."}), 403  # Forbidden

    # Get the movie_id and rating from the request body
    data = request.get_json()
    movie_id = data.get('movie_id')
    rating = data.get('rating')

    # Check if the movie exists in the database
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
    
@app.route('/all_ratings', methods=['GET'])
@jwt_required()
def get_all_ratings():
    current_user = get_jwt_identity()

    try:
        # Fetch all ratings with movie titles
        cursor = mysql.connection.cursor()
        query = """
            SELECT 
                r.id AS rating_id, 
                r.username, 
                r.rating, 
                m.title AS movie_title
            FROM 
                ratings r 
            JOIN 
                movies m ON r.movie_id = m.id
        """
        cursor.execute(query)
        ratings = cursor.fetchall()

        if not ratings:
            return jsonify({"message": "No ratings found"}), 404

        return jsonify(ratings), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to retrieve ratings"}), 500


@app.route('/movies/<int:movie_id>', methods=['GET'])
@jwt_required()
def get_movie_details(movie_id):
    current_user = get_jwt_identity()

    try:
        # Fetch movie details from the 'movies' table
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        movie = cursor.fetchone()

        if not movie:
            return jsonify({"message": "Movie not found"}), 404

        # Fetch all ratings for the given movie from the 'ratings' table
        cursor.execute("SELECT username, rating FROM ratings WHERE movie_id = %s", (movie_id,))
        ratings = cursor.fetchall()

        # Combine movie details with ratings
        movie_details = {
            "id": movie['id'],
            "title": movie['title'],
            "description": movie['description'],
            "ratings": ratings
        }

        return jsonify(movie_details), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to fetch movie details"}), 500


@app.route('/ratings/<int:movie_id>', methods=['PUT'])
@jwt_required()
def update_rating(movie_id):
    current_user = get_jwt_identity()

    # Get the new rating from the request body
    data = request.get_json()
    new_rating = data.get('rating')

    if new_rating is None:
        return jsonify({"message": "New rating is required"}), 400

    try:
        # Check if the rating exists for the current user and movie
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM ratings WHERE username = %s AND movie_id = %s"
        cursor.execute(query, (current_user, movie_id))
        rating = cursor.fetchone()

        if not rating:
            return jsonify({"message": "No existing rating found for this movie"}), 404

        # Update the user's rating for the movie
        update_query = "UPDATE ratings SET rating = %s WHERE username = %s AND movie_id = %s"
        cursor.execute(update_query, (new_rating, current_user, movie_id))
        mysql.connection.commit()

        return jsonify({"message": "Rating updated successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to update rating"}), 500
    
@app.route('/ratings/<int:rating_id>', methods=['DELETE'])
@jwt_required()
def delete_rating(rating_id):
    current_user = get_jwt_identity()  # Get the username from JWT token

    try:
        # Retrieve the user's role from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT role FROM users WHERE username = %s", (current_user,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        # If the user is an admin, they can delete any rating
        if user['role'] == 'admin':
            delete_query = "DELETE FROM ratings WHERE id = %s"
            cursor.execute(delete_query, (rating_id,))
            mysql.connection.commit()
            return jsonify({"message": "Rating deleted successfully (Admin)!"}), 200

        # If the user is not an admin, check if the rating belongs to them
        query = "SELECT * FROM ratings WHERE id = %s AND username = %s"
        cursor.execute(query, (rating_id, current_user))
        rating = cursor.fetchone()

        if not rating:
            return jsonify({"message": "No rating found or unauthorized to delete"}), 404

        # If the rating belongs to the user, delete it
        delete_query = "DELETE FROM ratings WHERE id = %s"
        cursor.execute(delete_query, (rating_id,))
        mysql.connection.commit()
        return jsonify({"message": "Rating deleted successfully (User)!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Failed to delete rating"}), 500


if __name__ == '__main__':
    app.run(debug=True)
