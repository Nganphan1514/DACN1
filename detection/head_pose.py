import cv2
import numpy as np


def get_head_pose(face_landmarks, w, h):

    try:

        face_2d = []
        face_3d = []

        landmark_ids = [33, 263, 1, 61, 291, 199]

        for idx in landmark_ids:

            lm = face_landmarks.landmark[idx]

            x = int(lm.x * w)

            y = int(lm.y * h)

            face_2d.append([x, y])

            face_3d.append([x, y, lm.z])

        face_2d = np.array(face_2d, dtype=np.float64)

        face_3d = np.array(face_3d, dtype=np.float64)

        focal_length = w

        cam_matrix = np.array(
            [[focal_length, 0, w / 2], [0, focal_length, h / 2], [0, 0, 1]]
        )

        dist_matrix = np.zeros((4, 1), dtype=np.float64)

        success, rot_vec, trans_vec = cv2.solvePnP(
            face_3d, face_2d, cam_matrix, dist_matrix
        )

        if not success:

            return (0, 0)

        rmat, _ = cv2.Rodrigues(rot_vec)

        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

        pitch = round(angles[0], 2)

        yaw = round(angles[1], 2)

        return (pitch, yaw)

    except Exception as e:

        print("Loi head pose:", e)

        return (0, 0)
