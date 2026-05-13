import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
import joblib
import os

# ======================
# Đọc dataset
# ======================
file_path = "dataset/drowsiness_dataset.csv"

df = pd.read_csv(file_path)

print("===== 5 dong dau =====")
print(df.head())

# ======================
# Chia dữ liệu
# X = feature
# y = label
# ======================
X = df[["EAR", "MAR"]]

y = df["Label"]

# ======================
# Chia train/test
# 80% train
# 20% test
# ======================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# ======================
# Khởi tạo model SVM
# ======================
model = SVC(
    kernel="rbf"
)

# ======================
# Train model
# ======================
print("\nDang train model...")

model.fit(
    X_train,
    y_train
)

print("Train xong!")

# ======================
# Dự đoán
# ======================
y_pred = model.predict(X_test)

# ======================
# Accuracy
# ======================
accuracy = accuracy_score(
    y_test,
    y_pred
)

print("\n===== KET QUA =====")
print(f"Do chinh xac: {accuracy:.2f}")

print("\n===== REPORT =====")
print(
    classification_report(
        y_test,
        y_pred
    )
)

# ======================
# Lưu model
# ======================
os.makedirs(
    "model",
    exist_ok=True
)

joblib.dump(
    model,
    "model/drowsy_model.pkl"
)

print("\nDa luu model!")
print("model/drowsy_model.pkl")