from celery import Celery

celery = Celery(
    "worklog",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def add_numbers(a, b):
    return a + b

@celery.task
def log_task_creation(task_id, title):
    print(f"Task created: #{task_id} - {title}")
    return {
        "task_id": task_id,
        "message": "Task creation logged successfully"
    }