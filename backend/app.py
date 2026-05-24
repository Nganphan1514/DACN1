from flask import Flask
from flask_cors import CORS
from backend.routes.dashboard_routes import dashboard_bp

from backend.routes.auth_routes import auth_bp

app = Flask(__name__, 
            template_folder="templates", 
            static_folder="static")

app.register_blueprint(dashboard_bp)

CORS(app)

# REGISTER ROUTES
app.register_blueprint(auth_bp)


@app.route("/")
def home():

    return "Backend Running"


if __name__ == "__main__":

    app.run(debug=True, port=5000)
