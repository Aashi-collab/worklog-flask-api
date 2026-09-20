# WorkLog 

WorkLog is a Flask-based social productivity platform where users can create profiles, share work updates, connect with other users, like posts, and comment on posts.

## Features

- User registration and login
- Secure password hashing
- Session-based authentication
- User profiles
- Create and view work posts
- Like / Unlike posts
- Comment on posts
- Follow / Unfollow users
- Followers and Following count
- MongoDB Atlas database
- Celery background task processing
- Redis message broker
- REST API endpoints
- Task management with status and priority
- Task filtering
- Git and GitHub version control

## Tech Stack

- Python
- Flask
- MongoDB Atlas
- PyMongo
- Celery
- Redis
- HTML
- Bootstrap
- Jinja2
- Git & GitHub

## Project Structure

```text
worklog/
│
├── app.py
├── celery_app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── profile.html
│
├── static/
│   └── css/
│
├── test_api.py
└── test_mongodb.py

## API Endpoints

### User
- POST /users
- POST /login

### Tasks
- GET /tasks
- POST /tasks
- PUT /tasks/<task_id>
- DELETE /tasks/<task_id>

### Social Features
- POST /posts
- POST /posts/<post_id>/like
- POST /posts/<post_id>/comment
- POST /users/<user_id>/follow