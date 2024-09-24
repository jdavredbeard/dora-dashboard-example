from flask import Flask, jsonify
import random

app = Flask(__name__)

# @app.route('/')
# def random_error():
#     # Generate a random number between 0 and 9
#     random_number = random.randint(0, 9)

#     # 40% chance of success
#     if random_number < 4:
#         return jsonify({"status": "success", "message": "Everything is fine, nothing to see here!"})

#     else:
#         # Simulate an unhandled exception
#         raise Exception("Random unhandled exception occurred!")

@app.route('/')
def healthy():
    return jsonify({"status": "success", "message": "Everything is fine, nothing to see here!"})

if __name__ == '__main__':
    app.run(debug=True)