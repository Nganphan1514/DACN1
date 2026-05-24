import cv2

from face_auth.face_encoder import ma_hoa_khuon_mat

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)

cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)

    cv2.putText(
        frame,
        "Nhan S de test face",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
    )

    cv2.imshow("Test Face", frame)

    key = cv2.waitKey(1)

    if key == ord("s"):

        encoding = ma_hoa_khuon_mat(frame)

        if encoding:

            print("Ma hoa thanh cong!")

            print("So chieu:", len(encoding))

        else:

            print("Khong tim thay khuon mat")

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
