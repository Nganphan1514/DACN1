import cv2
import mediapipe as mp
import time

# MediaPipe
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)

drawing = mp.solutions.drawing_utils
drawing_style = mp.solutions.drawing_styles

# Landmark groups
LEFT_EYE = mp_face_mesh.FACEMESH_LEFT_EYE
RIGHT_EYE = mp_face_mesh.FACEMESH_RIGHT_EYE
LIPS = mp_face_mesh.FACEMESH_LIPS
IRISES = mp_face_mesh.FACEMESH_IRISES

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

prev_time = 0

while cap.isOpened():

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    rgb_frame.flags.writeable = False
    results = face_mesh.process(rgb_frame)
    rgb_frame.flags.writeable = True

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            # ===== VẼ EYE =====
            drawing.draw_landmarks(
                frame,
                face_landmarks,
                LEFT_EYE,
                None,
                drawing_style.get_default_face_mesh_contours_style()
            )

            drawing.draw_landmarks(
                frame,
                face_landmarks,
                RIGHT_EYE,
                None,
                drawing_style.get_default_face_mesh_contours_style()
            )

            # ===== VẼ MOUTH =====
            drawing.draw_landmarks(
                frame,
                face_landmarks,
                LIPS,
                None,
                drawing_style.get_default_face_mesh_contours_style()
            )

            # ===== VẼ IRIS =====
            drawing.draw_landmarks(
                frame,
                face_landmarks,
                IRISES,
                None,
                drawing_style.get_default_face_mesh_iris_connections_style()
            )

            # ========= ZOOM EYE =========
            eye_points = []

            eye_idx = [33, 133, 362, 263]

            for idx in eye_idx:
                p = face_landmarks.landmark[idx]

                x = int(p.x * w)
                y = int(p.y * h)

                eye_points.append((x, y))

            x_eye = [p[0] for p in eye_points]
            y_eye = [p[1] for p in eye_points]

            x1 = max(min(x_eye) - 80, 0)
            y1 = max(min(y_eye) - 80, 0)

            x2 = min(max(x_eye) + 80, w)
            y2 = min(max(y_eye) + 80, h)

            eye_roi = frame[y1:y2, x1:x2]

            if eye_roi.size > 0:

                zoom_eye = cv2.resize(
                    eye_roi,
                    (250, 150)
                )

                frame[20:170, w - 270:w - 20] = zoom_eye

                cv2.putText(
                    frame,
                    "EYE ZOOM",
                    (w - 250, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2
                )

            # ========= ZOOM MOUTH =========
            mouth_points = []

            mouth_idx = [61, 291, 13, 14]

            for idx in mouth_idx:
                p = face_landmarks.landmark[idx]

                x = int(p.x * w)
                y = int(p.y * h)

                mouth_points.append((x, y))

            x_mouth = [p[0] for p in mouth_points]
            y_mouth = [p[1] for p in mouth_points]

            x1 = max(min(x_mouth) - 80, 0)
            y1 = max(min(y_mouth) - 80, 0)

            x2 = min(max(x_mouth) + 80, w)
            y2 = min(max(y_mouth) + 80, h)

            mouth_roi = frame[y1:y2, x1:x2]

            if mouth_roi.size > 0:

                zoom_mouth = cv2.resize(
                    mouth_roi,
                    (250, 150)
                )

                frame[190:340, w - 270:w - 20] = zoom_mouth

                cv2.putText(
                    frame,
                    "MOUTH ZOOM",
                    (w - 250, 185),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2
                )

    # ===== FPS =====
    current_time = time.time()

    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow(
        "Drowsiness Detection",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()