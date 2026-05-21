from flask import Flask
from flask import render_template
from flask import Response

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
import glob
import joblib

app = Flask(__name__)

# ======================
# LOAD MODEL
# ======================
model = joblib.load(
    "model/drowsy_model.pkl"
)

# ======================
# MEDIAPIPE
# ======================
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True
)

# ======================
# LANDMARK
# ======================
LEFT_EYE = [
    33, 160, 158,
    133, 153, 144
]

RIGHT_EYE = [
    362, 385, 387,
    263, 373, 380
]

MOUTH = [
    61, 13,
    291, 14
]

LOG_FILE = (
    "logs/detection_log.csv"
)

camera = cv2.VideoCapture(0)


# ======================
# DISTANCE
# ======================
def distance(p1, p2):
    return np.linalg.norm(
        np.array(p1) - np.array(p2)
    )


# ======================
# EAR
# ======================
def calculate_ear(points):

    A = distance(
        points[1],
        points[5]
    )

    B = distance(
        points[2],
        points[4]
    )

    C = distance(
        points[0],
        points[3]
    )

    return (
        A + B
    ) / (2 * C)


# ======================
# MAR
# ======================
def calculate_mar(points):

    vertical = distance(
        points[1],
        points[3]
    )

    horizontal = distance(
        points[0],
        points[2]
    )

    return (
        vertical /
        horizontal
    )


# ======================
# CAMERA STREAM
# ======================
def generate_frames():

    while True:

        success, frame = (
            camera.read()
        )

        if not success:
            break

        frame = cv2.flip(
            frame,
            1
        )

        h, w, _ = frame.shape

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = (
            face_mesh.process(rgb)
        )

        status = (
            "KHONG TIM THAY MAT"
        )

        color = (
            255,
            255,
            255
        )

        ear = 0
        mar = 0

        if (
            results
            .multi_face_landmarks
        ):

            landmarks = (
                results
                .multi_face_landmarks[0]
            )

            left_eye = []
            right_eye = []
            mouth = []

            # LEFT EYE
            for idx in LEFT_EYE:

                p = (
                    landmarks
                    .landmark[idx]
                )

                x = int(
                    p.x * w
                )

                y = int(
                    p.y * h
                )

                left_eye.append(
                    (x, y)
                )

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0,255,0),
                    -1
                )

            # RIGHT EYE
            for idx in RIGHT_EYE:

                p = (
                    landmarks
                    .landmark[idx]
                )

                x = int(
                    p.x * w
                )

                y = int(
                    p.y * h
                )

                right_eye.append(
                    (x, y)
                )

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0,255,0),
                    -1
                )

            # MOUTH
            for idx in MOUTH:

                p = (
                    landmarks
                    .landmark[idx]
                )

                x = int(
                    p.x * w
                )

                y = int(
                    p.y * h
                )

                mouth.append(
                    (x, y)
                )

                cv2.circle(
                    frame,
                    (x, y),
                    3,
                    (0,0,255),
                    -1
                )

            left_ear = (
                calculate_ear(
                    left_eye
                )
            )

            right_ear = (
                calculate_ear(
                    right_eye
                )
            )

            ear = (
                left_ear +
                right_ear
            ) / 2

            mar = (
                calculate_mar(
                    mouth
                )
            )

            # ======================
            # AI PREDICT
            # ======================
            data = np.array([
                [ear, mar]
            ])

            prediction = (
                model.predict(
                    data
                )[0]
            )

            if prediction == 0:

                status = (
                    "TINH TAO"
                )

                color = (
                    0,
                    255,
                    0
                )

            elif prediction == 1:

                status = (
                    "NGAP / MET"
                )

                color = (
                    0,
                    165,
                    255
                )

            elif prediction == 2:

                status = (
                    "BUON NGU"
                )

                color = (
                    0,
                    0,
                    255
                )

            # DISPLAY
            cv2.putText(
                frame,
                f"EAR: {ear:.2f}",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,255,0),
                2
            )

            cv2.putText(
                frame,
                f"MAR: {mar:.2f}",
                (20,80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,0,255),
                2
            )

            cv2.putText(
                frame,
                status,
                (20,130),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                color,
                3
            )

        _, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        frame = (
            buffer.tobytes()
        )

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )


@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype=
        "multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/")
def dashboard():

    return render_template(
        "dashboard.html"
    )


if __name__ == "__main__":

    app.run(
        debug=True
    )