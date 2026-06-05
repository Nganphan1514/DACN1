import cv2
import mediapipe as mp
import os


# PATH

MODEL_PATH = "model/face_model.yml"

LABEL_PATH = "model/face_labels.txt"



# LOAD MODEL

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(MODEL_PATH)

label_map = {}

if os.path.exists(LABEL_PATH):

    with open(LABEL_PATH, "r", encoding="utf-8") as file:

        for line in file:

            key, value = line.strip().split(":")

            label_map[int(key)] = value



# MEDIAPIPE

mp_face_detection = mp.solutions.face_detection

face_detector = mp_face_detection.FaceDetection(min_detection_confidence=0.5)



# RECOGNIZE DRIVER

def recognize_driver(frame):

    try:

        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = face_detector.process(rgb)

        if not results.detections:

            return (None, 0)

        detection = results.detections[0]

        bbox = detection.location_data.relative_bounding_box

        x = int(bbox.xmin * w)

        y = int(bbox.ymin * h)

        bw = int(bbox.width * w)

        bh = int(bbox.height * h)

        padding = 20

        x1 = max(0, x - padding)

        y1 = max(0, y - padding)

        x2 = min(w, x + bw + padding)

        y2 = min(h, y + bh + padding)

        face_crop = frame[y1:y2, x1:x2]

        if face_crop.size == 0:

            return (None, 0)

        gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

        gray_face = cv2.resize(gray_face, (200, 200))

        label, confidence = recognizer.predict(gray_face)

        # confidence càng thấp càng giống
        similarity = max(0, 100 - confidence)

        if similarity < 45:

            return (None, similarity)

        folder_name = label_map.get(label)

        if not folder_name:

            return (None, similarity)

        # tai_xe_3 -> 3
        tai_xe_id = int(folder_name.replace("tai_xe_", ""))

        return (tai_xe_id, similarity)

    except Exception as e:

        print("Face recognize error:", e)

        return (None, 0)



# TEST

if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.flip(frame, 1)

        tai_xe_id, do_tuong_dong = recognize_driver(frame)

        text = "Khong xac dinh"

        color = (0, 0, 255)

        if tai_xe_id:

            text = f"Tai xe: " f"{tai_xe_id}"

            color = (0, 255, 0)

        cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.putText(
            frame,
            f"Similarity: " f"{do_tuong_dong:.1f}%",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Nhan dien tai xe", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
