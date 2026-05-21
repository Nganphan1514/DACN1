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

print("===== 5 DÒNG ĐẦU =====")
print(df.head())

# ======================
# Feature và Label
# ======================
X = df[["EAR", "MAR"]]

y = df["Label"]

# ======================
# Chia train/test
# ======================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ======================
# Khởi tạo model
# ======================
model = SVC(
    kernel="rbf",
    probability=True
)

print("\nĐang train model...")

# ======================
# Train
# ======================
model.fit(
    X_train,
    y_train
)

print("Train xong!")

# ======================
# Predict
# ======================
y_pred = model.predict(X_test)

# ======================
# Accuracy
# ======================
accuracy = accuracy_score(
    y_test,
    y_pred
)

print("\n===== KẾT QUẢ =====")
print(
    f"Độ chính xác: {accuracy:.2f}"
)

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

print("\nĐã lưu model:")
print("model/drowsy_model.pkl")