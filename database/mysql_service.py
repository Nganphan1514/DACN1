import mysql.connector
from datetime import datetime

connection = (
    mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database=(
            "driver_monitoring"
        )
    )
)

cursor = connection.cursor()


def save_detection_log(
    ear,
    mar,
    blink_count,
    perclos,
    pitch,
    risk_score,
    status
):

    query = """
    INSERT INTO
    detection_logs
    (
        timestamp,
        ear,
        mar,
        blink_count,
        perclos,
        pitch,
        risk_score,
        status
    )
    VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        datetime.now(),

        float(ear),

        float(mar),

        int(blink_count),

        float(perclos),

        float(pitch),

        int(risk_score),

        status
    )

    cursor.execute(
        query,
        values
    )

    connection.commit()