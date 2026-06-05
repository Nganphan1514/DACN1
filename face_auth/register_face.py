import cv2
import mediapipe as mp
import os


# MEDIAPIPE FACE DETECTOR

mp_face_detection = mp.solutions.face_detection

face_detector = mp_face_detection.FaceDetection(min_detection_confidence=0.5)



# ĐĂNG KÝ KHUÔN MẶT

def dang_ky_khuon_mat(tai_xe_id, so_anh=60):

    BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

    folder = os.path.join(
        BASE_DIR,
        "dataset_faces",
        f"tai_xe_{tai_xe_id}"
    )

    print(folder)

    os.makedirs(folder, exist_ok=True)

    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)

    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    dem_anh = 0

    print("Bat dau dang ky khuon mat...")

    print("Nhan S de chup")

    print("Nhan Q de thoat")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = face_detector.process(rgb)

        co_mat = False
        face_crop = None

        if results.detections:

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

            co_mat = True

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.putText(
            frame,
            f"Da chup: {dem_anh}/{so_anh}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            frame,
            "Nhan S de chup",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Dang ky khuon mat", frame)

        key = cv2.waitKey(1)

        
        # CHỤP ẢNH
        
        if key == ord("s") and co_mat:

            gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

            gray_face = cv2.resize(gray_face, (200, 200))

            file_path = f"{folder}/{dem_anh+1}.jpg"

            cv2.imwrite(file_path, gray_face)

            dem_anh += 1

            print(f"Da luu {file_path}")

        elif key == ord("q"):
            break

        if dem_anh >= so_anh:
            break

    cap.release()

    cv2.destroyAllWindows()

    print("Dang ky thanh cong!")



# TEST

if __name__ == "__main__":

    tai_xe_id = int(input("Nhap ID tai xe: "))

    dang_ky_khuon_mat(tai_xe_id)
