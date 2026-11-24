
from typing import Any
from flask import Flask, jsonify, request, send_from_directory, render_template

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# In-memory "databases"
users = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}


# Health endpoint
@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "All good"}), 200


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_object(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404


# Helper functions for managing orders

def get_user_object(user_id:str) -> Any:
    if user_id in users:
        return users[user_id]
    else:
        return None

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5031, debug=True)