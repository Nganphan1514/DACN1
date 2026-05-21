from flask import Flask
from flask_cors import CORS
from flask import render_template

from routes import register_routes

app = Flask(__name__)

CORS(app)

register_routes(app)


@app.route("/")
def dashboard():

    return render_template("dashboard.html")


if __name__ == "__main__":

    app.run(debug=True, port=5000)
