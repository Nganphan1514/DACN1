from flask import Flask, redirect
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from backend.routes.auth_routes import auth_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.driver_routes import driver_bp
from backend.routes.report_routes import report_bp
from backend.routes.admin_routes import admin_bp
from backend.routes.scheduler_routes import scheduler_bp
app = Flask(__name__)

app.config["SECRET_KEY"] = "dacn1-secret-key"
app.config["JWT_SECRET_KEY"] = "dacn1-jwt-secret-key"

CORS(app)
jwt = JWTManager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(driver_bp)
app.register_blueprint(report_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(scheduler_bp)
@app.route("/")
def index():
    return redirect("/login")

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False,
        threaded=False
    )