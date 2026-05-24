import pandas as pd
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix

# ======================
# PATH
# ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

dataset_path = os.path.join(BASE_DIR, "dataset", "drowsiness_dataset.csv")

model_folder = os.path.join(BASE_DIR, "model")

os.makedirs(model_folder, exist_ok=True)

model_path = os.path.join(model_folder, "drowsy_model.pkl")

scaler_path = os.path.join(model_folder, "scaler.pkl")

# ======================
# Đọc dataset
# ======================
print("Dang doc dataset...")

if not os.path.exists(dataset_path):

    print("Khong tim thay dataset!")
    print(dataset_path)

    exit()

df = pd.read_csv(dataset_path)

print("\n===== 5 DONG DAU =====")
print(df.head())

print("\n===== THONG TIN DATASET =====")
print(df.info())

print("\n===== SO LUONG LABEL =====")
print(df["Label"].value_counts())

# ======================
# Feature và Label
# ======================
X = df[["EAR", "MAR"]]
y = df["Label"]

# ======================
# Chia train/test
# ======================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("\nDa chia train/test")

# ======================
# Chuẩn hóa dữ liệu
# ======================
scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

X_test_scaled = scaler.transform(X_test)

# ======================
# Khởi tạo model SVM
# ======================
model = SVC(kernel="rbf", probability=True, C=10, gamma="scale")

print("\nDang train model SVM...")

# ======================
# Train
# ======================
model.fit(X_train_scaled, y_train)

print("Train xong!")

# ======================
# Predict
# ======================
y_pred = model.predict(X_test_scaled)

# ======================
# Accuracy
# ======================
accuracy = accuracy_score(y_test, y_pred)

print("\n===== KET QUA =====")

print(f"Do chinh xac: {accuracy * 100:.2f}%")

# ======================
# Classification report
# ======================
print("\n===== CLASSIFICATION REPORT =====")

print(classification_report(y_test, y_pred))

# ======================
# Confusion Matrix
# ======================
print("\n===== CONFUSION MATRIX =====")

print(confusion_matrix(y_test, y_pred))

# ======================
# Lưu model
# ======================
joblib.dump(model, model_path)

joblib.dump(scaler, scaler_path)

print("\n===== DA LUU MODEL =====")
print(model_path)

print("\n===== DA LUU SCALER =====")
print(scaler_path)

print("\nTrain model thanh cong!")
