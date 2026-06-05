import cv2
import os
import numpy as np


# PATH

DATASET_PATH = "dataset_faces"

MODEL_FOLDER = "model"

MODEL_PATH = "model/face_model.yml"

LABEL_PATH = "model/face_labels.txt"

os.makedirs(MODEL_FOLDER, exist_ok=True)



# TRAIN MODEL

def train_model():

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    faces = []

    labels = []

    label_map = {}

    current_label = 0

    print("Dang doc dataset...")

    if not os.path.exists(DATASET_PATH):

        print("Khong tim thay dataset_faces")

        return

    folders = os.listdir(DATASET_PATH)

    for folder in folders:

        folder_path = os.path.join(DATASET_PATH, folder)

        if not os.path.isdir(folder_path):
            continue

        print(f"Dang doc: {folder}")

        label_map[current_label] = folder

        image_files = os.listdir(folder_path)

        for image_name in image_files:

            image_path = os.path.join(folder_path, image_name)

            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            if image is None:
                continue

            faces.append(image)

            labels.append(current_label)

        current_label += 1

    if len(faces) == 0:

        print("Khong co du lieu train")

        return

    labels = np.array(labels)

    print("\nDang train model...")

    recognizer.train(faces, labels)

    recognizer.save(MODEL_PATH)

    
    # SAVE LABEL MAP
    
    with open(LABEL_PATH, "w", encoding="utf-8") as file:

        for key, value in label_map.items():

            file.write(f"{key}:{value}\n")

    print("\nTrain thanh cong!")

    print("Model:", MODEL_PATH)

    print("Label:", LABEL_PATH)

    print(f"So nguoi: {len(label_map)}")

    print(f"So anh: {len(faces)}")



# RUN

if __name__ == "__main__":

    train_model()
