from datetime import timedelta

from flask import Flask, redirect, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config.app_config import (
    DEBUG,
    FLASK_HOST,
    FLASK_PORT,
    JWT_SECRET_KEY,
    SECRET_KEY,
)
from backend.routes.admin_routes import admin_bp
from backend.routes.ai_monitor_routes import ai_monitor_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.driver_routes import driver_bp
from backend.routes.face_routes import face_bp
from backend.routes.org_routes import org_bp
from backend.routes.realtime_routes import realtime_bp
from backend.routes.report_routes import report_bp
from backend.routes.scheduler_routes import scheduler_bp

app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app)
jwt = JWTManager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(driver_bp)
app.register_blueprint(face_bp)
app.register_blueprint(org_bp)
app.register_blueprint(realtime_bp)
app.register_blueprint(report_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(ai_monitor_bp)
app.register_blueprint(scheduler_bp)


@app.route("/")
def index():
    return redirect("/login")


@app.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")


if __name__ == "__main__":
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=DEBUG,
        use_reloader=False,
        threaded=True,
    )
