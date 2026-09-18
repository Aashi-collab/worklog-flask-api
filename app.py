from flask import Flask, jsonify, request

app = Flask(__name__)


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
    return jsonify(users_list)


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    new_user = {
        "id": len(users_list) + 1,
        "name": data["name"]
    }

    users_list.append(new_user)

    return jsonify(new_user), 201

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()

    for user in users_list:
        if user["id"] == user_id:
            user["name"] = data["name"]
            return jsonify(user)

    return jsonify({"error": "User not found"}), 404

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    for user in users_list:
        if user["id"] == user_id:
            users_list.remove(user)
            return jsonify({"message": "User deleted successfully"})

    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)