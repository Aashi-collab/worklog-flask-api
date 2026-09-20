from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from celery_app import add_numbers, log_task_creation

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "worklog-development-secret")

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

db = client["worklog"]

users_collection = db["users"]
tasks_collection = db["tasks"]
posts_collection = db["posts"]


# =========================
# HOME
# =========================

@app.route("/")
def home():
    posts = list(
        posts_collection.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1)
    )

    return render_template(
        "index.html",
        posts=posts
    )


# =========================
# USER ROUTES
# =========================

@app.route("/users", methods=["GET"])
def get_users():

    users = list(
        users_collection.find(
            {},
            {"_id": 0, "password": 0}
        )
    )

    return jsonify(users)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    if not name or not email or not password:
        flash("All fields are required.")
        return redirect(url_for("register"))

    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        flash("An account with this email already exists.")
        return redirect(url_for("register"))

    new_user = {
        "id": users_collection.count_documents({}) + 1,
        "name": name,
        "email": email,
        "password": generate_password_hash(password)
    }

    users_collection.insert_one(new_user)

    flash("Account created successfully. Please login.")
    return redirect(url_for("login"))


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

    response_user = {
        "id": new_user["id"],
        "name": new_user["name"],
        "email": new_user["email"],
        "_id": str(result.inserted_id)
    }

    return jsonify(response_user), 201

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    if not data or "email" not in data or "password" not in data:
        if request.is_json:
            return jsonify({"error": "Email and password are required"}), 400

        flash("Email and password are required.")
        return redirect(url_for("login"))

    user = users_collection.find_one({"email": data["email"]})

    if not user or not check_password_hash(user["password"], data["password"]):
        if request.is_json:
            return jsonify({"error": "Invalid email or password"}), 401

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    session["user_id"] = user["id"]

    if request.is_json:
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        }), 200

    return redirect(url_for("profile"))


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):

    data = request.get_json()

    if not data or "name" not in data:
        return jsonify({
            "error": "Name is required"
        }), 400

    result = users_collection.update_one(
        {"id": user_id},
        {"$set": {"name": data["name"]}}
    )

    if result.matched_count == 0:
        return jsonify({
            "error": "User not found"
        }), 404

    updated_user = users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "password": 0}
    )

    return jsonify(updated_user)


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):

    result = users_collection.delete_one({
        "id": user_id
    })

    if result.deleted_count == 0:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "message": "User deleted successfully"
    })

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = users_collection.find_one(
        {"id": session["user_id"]},
        {"_id": 0, "password": 0}
    )

    if not user:
        session.clear()
        return redirect(url_for("login"))

    following_count = len(user.get("following", []))

    followers_count = users_collection.count_documents(
        {"following": session["user_id"]}
    )

    my_posts = list(
        posts_collection.find(
            {"user_id": session["user_id"]},
            {"_id": 0}
        ).sort("created_at", -1)
    )

    return render_template(
        "profile.html",
        user=user,
        followers_count=followers_count,
        following_count=following_count,
        posts=my_posts
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))

@app.route("/posts", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form.get("content", "").strip()

    if not content:
        flash("Post cannot be empty.")
        return redirect(url_for("home"))

    user = users_collection.find_one(
        {"id": session["user_id"]}
    )

    if not user:
        session.clear()
        return redirect(url_for("login"))

    new_post = {
        "id": posts_collection.count_documents({}) + 1,
        "user_id": user["id"],
        "author_name": user["name"],
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "likes": [],
        "comments": []
    }

    posts_collection.insert_one(new_post)

    flash("Post published successfully!")
    return redirect(url_for("home"))


@app.route("/posts/<int:post_id>/like", methods=["POST"])
def like_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    post = posts_collection.find_one({"id": post_id})

    if not post:
        flash("Post not found.")
        return redirect(url_for("home"))

    likes = post.get("likes", [])

    if user_id in likes:
        likes.remove(user_id)
        message = "Post unliked."
    else:
        likes.append(user_id)
        message = "Post liked!"

    posts_collection.update_one(
        {"id": post_id},
        {"$set": {"likes": likes}}
    )

    flash(message)
    return redirect(url_for("home"))

@app.route("/posts/<int:post_id>/comment", methods=["POST"])
def comment_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form.get("comment", "").strip()

    if not content:
        flash("Comment cannot be empty.")
        return redirect(url_for("home"))

    post = posts_collection.find_one({"id": post_id})

    if not post:
        flash("Post not found.")
        return redirect(url_for("home"))

    user = users_collection.find_one({"id": session["user_id"]})

    if not user:
        session.clear()
        return redirect(url_for("login"))

    new_comment = {
        "user_id": user["id"],
        "author_name": user["name"],
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    posts_collection.update_one(
        {"id": post_id},
        {"$push": {"comments": new_comment}}
    )

    flash("Comment added!")
    return redirect(url_for("home"))


@app.route("/users/<int:user_id>/follow", methods=["POST"])
def follow_user(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_user_id = session["user_id"]

    if current_user_id == user_id:
        flash("You cannot follow yourself.")
        return redirect(url_for("home"))

    target_user = users_collection.find_one({"id": user_id})

    if not target_user:
        flash("User not found.")
        return redirect(url_for("home"))

    current_user = users_collection.find_one({"id": current_user_id})

    following = current_user.get("following", [])

    if user_id in following:
        following.remove(user_id)
        message = "User unfollowed."
    else:
        following.append(user_id)
        message = "User followed."

    users_collection.update_one(
        {"id": current_user_id},
        {"$set": {"following": following}}
    )

    flash(message)
    return redirect(url_for("home"))


# =========================
# CELERY CALCULATION
# =========================

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


# =========================
# TASK ROUTES
# =========================

@app.route("/tasks", methods=["POST"])
def create_task():

    data = request.get_json()

    if not data or "title" not in data:
        return jsonify({
            "error": "Title is required"
        }), 400

    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    # Validate status
    if status not in [
        "pending",
        "in_progress",
        "completed"
    ]:
        return jsonify({
            "error": "Invalid status"
        }), 400

    # Validate priority
    if priority not in [
        "low",
        "medium",
        "high"
    ]:
        return jsonify({
            "error": "Invalid priority"
        }), 400

    assigned_to = data.get("assigned_to")

    # Validate assigned user
    if assigned_to is not None:

        user = users_collection.find_one({
            "id": assigned_to
        })

        if not user:
            return jsonify({
                "error": "Assigned user not found"
            }), 404

    new_task = {
        "id": tasks_collection.count_documents({}) + 1,
        "title": data["title"],
        "description": data.get("description", ""),
        "assigned_to": assigned_to,
        "status": status,
        "priority": priority
    }

    # Save task in MongoDB
    result = tasks_collection.insert_one(new_task)

    # Background task using Celery
    log_task_creation.delay(
        new_task["id"],
        new_task["title"]
    )

    # JSON-safe response
    response_task = {
        "id": new_task["id"],
        "title": new_task["title"],
        "description": new_task["description"],
        "assigned_to": new_task["assigned_to"],
        "status": new_task["status"],
        "priority": new_task["priority"],
        "_id": str(result.inserted_id)
    }

    return jsonify(response_task), 201


@app.route("/tasks", methods=["GET"])
def get_tasks():

    query = {}

    status = request.args.get("status")
    priority = request.args.get("priority")
    assigned_to = request.args.get("assigned_to")

    if status:
        query["status"] = status

    if priority:
        query["priority"] = priority

    if assigned_to:

        try:
            query["assigned_to"] = int(assigned_to)

        except ValueError:
            return jsonify({
                "error": "assigned_to must be an integer"
            }), 400

    tasks = list(
        tasks_collection.find(
            query,
            {"_id": 0}
        )
    )

    return jsonify(tasks)


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request data is required"
        }), 400

    updates = {}

    # Allowed fields
    for field in [
        "title",
        "description",
        "assigned_to",
        "status",
        "priority"
    ]:

        if field in data:
            updates[field] = data[field]

    if not updates:
        return jsonify({
            "error": "No fields to update"
        }), 400

    # Validate status
    if "status" in updates:

        if updates["status"] not in [
            "pending",
            "in_progress",
            "completed"
        ]:
            return jsonify({
                "error": "Invalid status"
            }), 400

    # Validate priority
    if "priority" in updates:

        if updates["priority"] not in [
            "low",
            "medium",
            "high"
        ]:
            return jsonify({
                "error": "Invalid priority"
            }), 400

    # Validate assigned user
    if "assigned_to" in updates:

        assigned_to = updates["assigned_to"]

        if assigned_to is not None:

            user = users_collection.find_one({
                "id": assigned_to
            })

            if not user:
                return jsonify({
                    "error": "Assigned user not found"
                }), 404

    result = tasks_collection.update_one(
        {"id": task_id},
        {"$set": updates}
    )

    if result.matched_count == 0:
        return jsonify({
            "error": "Task not found"
        }), 404

    updated_task = tasks_collection.find_one(
        {"id": task_id},
        {"_id": 0}
    )

    return jsonify(updated_task)


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    result = tasks_collection.delete_one({
        "id": task_id
    })

    if result.deleted_count == 0:
        return jsonify({
            "error": "Task not found"
        }), 404

    return jsonify({
        "message": "Task deleted successfully"
    })

# RUN APPLICATION

if __name__ == "__main__":
    app.run(debug=True)