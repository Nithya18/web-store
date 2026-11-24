
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

# Order data
orders = {}
order_id_counter = 1

# Health endpoint
@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "All good"}), 200

@app.route('/', methods=['POST', 'PUT'])
def create_order():
    global order_id_counter

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid order data"}), 400

    user_id = data.get("user_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
           for value in (user_id, product_id, quantity)):
        return jsonify({"error": "user_id, product_id, and quantity must be positive integers"}), 400

    try:
        user = get_user_object(user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        product = get_product_object(product_id)
        if product is None:
            return jsonify({"error": "Product not found"}), 404
        if (not isinstance(product.get("stock"), int)
                or isinstance(product.get("stock"), bool)
                or product["stock"] < 0
                or not isinstance(product.get("price"), (int, float))
                or isinstance(product.get("price"), bool)):
            return jsonify({"error": "Invalid response from product service"}), 502
        if product["stock"] < quantity:
            return jsonify({"error": "Insufficient stock"}), 400

        update_stock(product_id, product["stock"] - quantity)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Dependent service timed out"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Dependent service unavailable"}), 503
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else 502
        if status_code == 404:
            return jsonify({"error": "Product not found"}), 404
        if status_code >= 500:
            return jsonify({"error": "Dependent service unavailable"}), 503
        return jsonify({"error": "Invalid response from dependent service"}), 502
    except requests.exceptions.JSONDecodeError:
        return jsonify({"error": "Invalid response from dependent service"}), 502

    order = {
        "id": order_id_counter,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "total": product["price"] * quantity,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    orders[order_id_counter] = order
    order_id_counter += 1
    return jsonify(order), 201

@app.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = orders.get(order_id)
    if order is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order), 200

def get_user_object(user_id: int):
    response = requests.get(
        f"http://127.0.0.1:5031/users/{user_id}",
        timeout=5
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    user = response.json()
    if not isinstance(user, dict):
        raise requests.exceptions.JSONDecodeError(
            "User service returned invalid data", response.text, 0
        )
    return user

def get_product_object(product_id: int):
    response = requests.get(
        f"http://127.0.0.1:5032/{product_id}",
        timeout=5
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    product = response.json()
    if not isinstance(product, dict):
        raise requests.exceptions.JSONDecodeError(
            "Product service returned invalid data", response.text, 0
        )
    return product


def update_stock(product_id: int, stock: int):
    response = requests.put(
        f"http://127.0.0.1:5032/{product_id}/stock",
        json={"stock": stock},
        timeout=5
    )
    response.raise_for_status()
    return response.json()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5033, debug=True)
