from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
from pymongo import MongoClient

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


users_list = [
    {"id": 1, "name": "Aashi"},
    {"id": 2, "name": "Rahul"},
    {"id": 3, "name": "Priya"}
]

@app.route("/users", methods=["GET"])
def get_users():
    users = list(users_collection.find({}, {"_id": 0}))
    return jsonify(users)


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    new_user = {
        "id": users_collection.count_documents({}) + 1,
        "name": data["name"]
    }

    result = users_collection.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)

    return jsonify(new_user), 201
    

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()

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

    return jsonify({"message": "User deleted successfully"})

if __name__ == "__main__":
    app.run(debug=True)