import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGO_URI")

client = MongoClient(uri)

client.admin.command("ping")

print("MongoDB connected successfully!")