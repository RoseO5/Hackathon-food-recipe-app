from flask import Flask, request, jsonify

# Define the Flask app
app = Flask(__name__)

# Simple GET route (test in browser at http://127.0.0.1:5000/)
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to the Recipe API!"})

# POST route for recipes
@app.route("/recipes", methods=["POST"])
def recipes():
    data = request.get_json()  # get JSON from request body
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return jsonify({"message": "Recipe added successfully!", "data": data})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
