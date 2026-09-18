import requests

response = requests.delete(
    "http://127.0.0.1:5000/users/3"
)

print(response.status_code)
print(response.json())