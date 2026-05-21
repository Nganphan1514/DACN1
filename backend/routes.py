from flask import jsonify
from database import get_connection


def register_routes(app):

    @app.route("/api/logs")
    def get_logs():

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM detection_logs
            ORDER BY id DESC
            LIMIT 100
            """)

        logs = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify(logs)

    @app.route("/api/status")
    def get_status():

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM detection_logs
            ORDER BY id DESC
            LIMIT 1
            """)

        status = cursor.fetchone()

        cursor.close()
        connection.close()

        return jsonify(status)

    import os

    @app.route("/api/snapshots")
    def get_snapshots():

        folder = "../snapshots"

        files = []

        if os.path.exists(folder):

            files = sorted(os.listdir(folder), reverse=True)

        return jsonify(files)
    @app.route(
    "/api/stats"
)
    def get_stats():

        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor(
                dictionary=True
            )
        )

        cursor.execute(
            """
            SELECT
            COUNT(*) as total,
            SUM(
                CASE
                WHEN status='BUON NGU'
                THEN 1
                ELSE 0
                END
            ) as sleepy_count
            FROM detection_logs
            """
        )

        stats = (
            cursor.fetchone()
        )

        cursor.close()
        connection.close()

        return jsonify(
            stats
        )

    @app.route(
    "/api/drivers"
)
    def get_drivers():

        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor(
                dictionary=True
            )
        )

        cursor.execute(
            """
            SELECT *
            FROM drivers
            """
        )

        drivers = (
            cursor.fetchall()
        )

        cursor.close()
        connection.close()

        return jsonify(
            drivers
        )

    @app.route(
    "/api/vehicles"
)
    def get_vehicles():

        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor(
                dictionary=True
            )
        )

        cursor.execute(
            """
            SELECT *
            FROM vehicles
            """
        )

        vehicles = (
            cursor.fetchall()
        )

        cursor.close()
        connection.close()

        return jsonify(
            vehicles
        )

    from flask import request


    @app.route("/api/login", methods=["POST"])
    def login_driver():

        data = request.json

        driver_id = data["driver_id"]

        vehicle_id = data["vehicle_id"]

        connection = get_connection()

        cursor = connection.cursor()

        # clear old session
        cursor.execute("""
            DELETE FROM
            active_session
            """)

        cursor.execute(
            """
            INSERT INTO
            active_session
            (
                driver_id,
                vehicle_id,
                login_time
            )
            VALUES
            (%s,%s,NOW())
            """,
            (driver_id, vehicle_id),
        )

        connection.commit()

        cursor.close()
        connection.close()

        return {"message": "login success"}
    
        @app.route(
            "/api/current-session"
        )
        def current_session():

            connection = (
                get_connection()
            )

            cursor = (
                connection.cursor(
                    dictionary=True
                )
            )

            cursor.execute(
                """
                SELECT
                d.full_name,
                v.plate_number,
                a.login_time
                FROM active_session a
                JOIN drivers d
                ON a.driver_id=d.id
                JOIN vehicles v
                ON a.vehicle_id=v.id
                LIMIT 1
                """
            )

            session = cursor.fetchone()

            cursor.close()
            connection.close()

            return jsonify(
                session
            )
