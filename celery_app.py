from celery import Celery

celery = Celery(
    "worklog",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def add_numbers(a, b):
    return a + b