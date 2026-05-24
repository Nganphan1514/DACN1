from flask import jsonify
from flask import request

from database.mysql_service import db

import os


def register_routes(app):

    # ==========================
    # REALTIME LOGS
    # ==========================
    @app.route("/api/logs")
    def get_logs():

        cursor = db.get_cursor()

        cursor.execute("""
            SELECT *
            FROM nhat_ky_phat_hien
            ORDER BY id DESC
            LIMIT 100
        """)

        logs = cursor.fetchall()

        cursor.close()

        return jsonify(logs)

    # ==========================
    # STATUS
    # ==========================
    @app.route("/api/status")
    def get_status():

        cursor = db.get_cursor()

        cursor.execute("""
            SELECT *
            FROM nhat_ky_phat_hien
            ORDER BY id DESC
            LIMIT 1
        """)

        status = cursor.fetchone()

        cursor.close()

        if not status:

            status = {
                "trang_thai": "KHONG CO DU LIEU",
                "risk_score": 0,
                "ear": 0,
                "mar": 0,
            }

        return jsonify(status)

    # ==========================
    # THỐNG KÊ
    # ==========================
    @app.route("/api/stats")
    def get_stats():

        cursor = db.get_cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                    WHEN trang_thai='BUON NGU'
                    THEN 1
                    ELSE 0
                    END
                ) AS sleepy_count

            FROM nhat_ky_phat_hien
        """)

        stats = cursor.fetchone()

        cursor.close()

        return jsonify(stats)

    # ==========================
    # TÀI XẾ
    # ==========================
    @app.route("/api/drivers")
    def get_drivers():

        cursor = db.get_cursor()

        cursor.execute("""
            SELECT *
            FROM tai_xe
        """)

        drivers = cursor.fetchall()

        cursor.close()

        return jsonify(drivers)

    # ==========================
    # XE
    # ==========================
    @app.route("/api/vehicles")
    def get_vehicles():

        cursor = db.get_cursor()

        cursor.execute("""
            SELECT *
            FROM xe
        """)

        vehicles = cursor.fetchall()

        cursor.close()

        return jsonify(vehicles)

    # ==========================
    # SNAPSHOTS
    # ==========================
    @app.route("/api/snapshots")
    def get_snapshots():

        folder = "../snapshots"

        files = []

        if os.path.exists(folder):

            files = sorted(os.listdir(folder), reverse=True)

        return jsonify(files)
