from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from celery_app import add_numbers

app = Flask(__name__)

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["worklog"]
users_collection = db["users"]


@app.route("/")
def home():
    return """
    <h1>WorkLog</h1>
    <p>A simple platform to share your work and daily updates.</p>
    """


@app.route("/users", methods=["GET"])
def get_users():
    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify(users)


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data or "name" not in data or "email" not in data or "password" not in data:
        return jsonify({
            "error": "Name, email and password are required"
        }), 400

    new_user = {
        "id": users_collection.count_documents({}) + 1,
        "name": data["name"],
        "email": data["email"],
        "password": generate_password_hash(data["password"])
    }

    result = users_collection.insert_one(new_user)

    new_user["_id"] = str(result.inserted_id)

    new_user.pop("password")

    return jsonify(new_user), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = users_collection.find_one({
        "email": data["email"]
    })

    if not user:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    if not check_password_hash(
        user["password"],
        data["password"]
    ):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }), 200


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()

    if not data or "name" not in data:
        return jsonify({"error": "Name is required"}), 400

    result = users_collection.update_one(
        {"id": user_id},
        {"$set": {"name": data["name"]}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    updated_user = users_collection.find_one(
        {"id": user_id},
        {"_id": 0}
    )

    return jsonify(updated_user)


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    result = users_collection.delete_one({"id": user_id})

    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "message": "User deleted successfully"
    })


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()

    if not data or "a" not in data or "b" not in data:
        return jsonify({
            "error": "a and b are required"
        }), 400

    task = add_numbers.delay(
        data["a"],
        data["b"]
    )

    return jsonify({
        "message": "Calculation started",
        "task_id": task.id
    }), 202


if __name__ == "__main__":
    app.run(debug=True)