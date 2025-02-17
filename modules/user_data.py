import json
import os

USER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_data.json')

# Upewnij się, że folder data istnieje
os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_user_avatar(username, avatar_filename):
    data = load_user_data()
    if username not in data:
        data[username] = {}
    data[username]['avatar'] = avatar_filename
    save_user_data(data)

def get_user_avatar(username):
    data = load_user_data()
    return data.get(username, {}).get('avatar')
