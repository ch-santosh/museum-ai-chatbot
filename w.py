import requests
import os

api_key = "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"
url = os.environ.get('FLASK_API_URL', 'http://localhost:5000')

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

print(response.json())