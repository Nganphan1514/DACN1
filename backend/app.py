from flask import Flask, render_template

from flask_cors import CORS

from routes import register_routes

app = Flask(__name__, template_folder="templates")

CORS(app)

register_routes(app)


@app.route("/")
def dashboard():

    return render_template("dashboard.html")


if __name__ == "__main__":

    app.run(debug=True, port=5000)
