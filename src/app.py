"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Favorites, Planets, People
import datetime
from flask_jwt_extended import JWTManager


#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/user', methods=['GET'])
def handle_hello():

    users = User.query.all()
    all_users = list(map(lambda x: x.serialize(), users))

    return jsonify(all_users), 200

@app.route('/users/<int:users_id>/favorites', methods=['GET'])
def get_user_favorite():
    user_favorites = Favorites.query.all()
    all_favorites = list(map(lambda x: x.serialize(), user_favorites))
    return jsonify(all_favorites), 200

@app.route('/people', methods=['GET'])
def get_people():
    people = People.query.all()
    all_peoples = list(map(lambda x: x.serialize(), people))
    return jsonify(all_peoples), 200

@app.route('/people/<int:people_id>', methods=['GET'])
def get_single_person(people_id):
    person = People.query.get(people_id)
    return jsonify(person.serialize()), 200 

@app.route('/planets', methods=['GET'])
def get_planets():
    planets = Planets.query.all()
    all_planets = list(map(lambda x: x.serialize(), planets))
    return jsonify(all_planets), 200

@app.route('/planets/<int:planets_id>', methods=['GET'])
def get_single_planet(planets_id):
    planet = Planets.query.get(planets_id)
    return jsonify(planet.serialize()), 200

@app.route('/favorite/planet/<int:planets_id>', methods=['POST'])
def post_favorite_planet(planets_id):
    planet = Planets.query.get(planets_id)
    if not planet:
        raise APIException('Planet not found', status_code=404)

    new_planet = Favorites(name=planet.name, planets_id=planets_id)
    db.session.add(new_planet)
    db.session.commit()
    return jsonify(new_planet.serialize()), 200


@app.route('/favorite/people/<int:people_id>', methods=['POST'])
def post_favorite_person(people_id):
    person = People.query.get(people_id)
    if not person:
        raise APIException('Person not found', status_code=404)

    new_person = Favorites(name=person.name, people_id=people_id)
    db.session.add(new_person)
    db.session.commit()
    return jsonify(new_person.serialize()), 200


@app.route('/favorite/planet/<int:planets_id>', methods=['DELETE'])
def delete_favorite_planet(planets_id):
    planet_favorite = Favorites.query.filter_by(planets_id=planets_id).first()
    if not planet_favorite:
        raise APIException('Favorite planet not found', status_code=404)
    
    db.session.delete(planet_favorite)
    db.session.commit() 
    return jsonify(planet_favorite.serialize()), 200


@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_people(people_id):
    people_favorite = Favorites.query.filter_by(people_id=people_id).first()
    if not people_favorite:
        raise APIException('Favorite person not found', status_code=404)
    
    db.session.delete(people_favorite)
    db.session.commit()  
    return jsonify(people_favorite.serialize()), 200


# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = "super-secret"  # Change this "super secret" with something else!
jwt = JWTManager(app)

from flask_jwt_extended import jwt_required, get_jwt_identity
# Protect a route with jwt_required, which will kick out requests
# without a valid JWT present.
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    return jsonify({"id": user.id, "username": user.username }), 200

from flask_jwt_extended import create_access_token

@app.route("/token", methods=["GET"])
def create_token():
    username = request.args.get("username", None)
    password = request.args.get("password", None)
    # Query your database for username and password
    user = User.query.filter_by(username=username, password=password).first()
    if user is None:
        # the user was not found on the database
        return jsonify({"msg": "Bad username or password"}), 401
    
    # create a new token with the user id inside
    access_token = create_access_token(identity=user.id)
    return jsonify({ "token": access_token, "user_id": user.id })

# Add the new route for creating a user with method GET
@app.route("/create-user", methods=["GET"])
def create_user():
    # Get user data from the request
    first_name = request.args.get("first_name", None)
    email = request.args.get("email", None)
    password = request.args.get("password", None)

    # Check if required fields are missing
    if not email or not password:
        return jsonify({"error": "Both email and password are required"}), 400

    # Check if the email already exists in the database
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 400

    # Hash the user password for security
    hashed_password = generate_password_hash(password, method="sha256")

    # Create a new User object and add it to the database
    new_user = User(
        first_name=first_name,
        email=email,
        password=hashed_password,
        is_active=True  
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User created successfully"}), 201

# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)