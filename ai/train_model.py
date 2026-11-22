import json
import os

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import (
    GroupKFold,
    GroupShuffleSplit,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2_DATASET_PATH = os.path.join(BASE_DIR, "dataset", "drowsiness_dataset_v2.csv")
LEGACY_DATASET_PATH = os.path.join(BASE_DIR, "dataset", "drowsiness_dataset.csv")

MODEL_DIR = os.path.join(BASE_DIR, "model")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "drowsy_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
META_PATH = os.path.join(MODEL_DIR, "model_meta.json")

V2_FEATURES = ["EAR", "MAR", "Pitch", "Yaw", "PERCLOS"]
LEGACY_FEATURES = ["EAR", "MAR"]


def clean_outliers(df):
    """
    Loc bo cac mau nhieu ro ret do chop mat luc bam phim hoac loi landmark:
    - Loai gia tri EAR <= 0 hoac NaN
    - Nhan 0 (Tinh tao): loai mau EAR < 0.16 (dinh chop mat)
    - Nhan 2 (Buon ngu): loai mau EAR > 0.28 (mat dang mo to)
    """
    before = len(df)
    df = df.dropna().copy()
    df = df[df["EAR"] > 0]

    mask_noise_awake = (df["Label"] == 0) & (df["EAR"] < 0.16)
    mask_noise_drowsy = (df["Label"] == 2) & (df["EAR"] > 0.28)
    df = df[~(mask_noise_awake | mask_noise_drowsy)]

    removed = before - len(df)
    print(f"Da loc {removed} mau nhieu (con lai {len(df)} mau sach).")
    return df


def choose_dataset():
    """
    Uu tien dataset v2 (5 dac trung) neu da thu du >= 150 mau va moi lop >= 30 mau.
    Nguoc lai dung dataset legacy (EAR, MAR).
    """
    if os.path.exists(V2_DATASET_PATH):
        df_v2 = pd.read_csv(V2_DATASET_PATH)
        if all(col in df_v2.columns for col in V2_FEATURES + ["Label"]):
            counts = df_v2["Label"].value_counts()
            if len(df_v2) >= 150 and len(counts) == 3 and counts.min() >= 30:
                print(f"Su dung dataset v2 (5 dac trung): {V2_DATASET_PATH}")
                return df_v2, V2_FEATURES, "v2_5features"

    if not os.path.exists(LEGACY_DATASET_PATH):
        raise FileNotFoundError(f"Khong tim thay dataset: {LEGACY_DATASET_PATH}")

    print(f"Su dung dataset legacy (2 dac trung EAR, MAR): {LEGACY_DATASET_PATH}")
    return pd.read_csv(LEGACY_DATASET_PATH), LEGACY_FEATURES, "legacy_2features"


def train():
    df, feature_cols, dataset_mode = choose_dataset()
    df = clean_outliers(df)

    print("\n===== PHAN BO NHAN SAU KHI LAM SACH =====")
    print(df["Label"].value_counts().sort_index())

    X = df[feature_cols]
    y = df["Label"].astype(int)

    # P0+ REV-10: Chong Data Leakage giua cac frame cung phien/nguoi bang GroupKFold
    has_groups = "SessionId" in df.columns and df["SessionId"].nunique() >= 2
    groups = df["SessionId"].astype(str) if has_groups else None

    if has_groups:
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(gss.split(X, y, groups))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        cv_splits = min(5, int(groups.nunique()))
        cv = GroupKFold(n_splits=cv_splits)
        cv_strategy = f"GroupKFold({cv_splits})_by_SessionId"
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_strategy = "StratifiedKFold(5)_frame_level"

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # class_weight="balanced" khac phuc mat can bang giua lop Buon ngu (2) va lop 0/1
    model = SVC(
        kernel="rbf",
        probability=True,
        C=10,
        gamma="scale",
        class_weight="balanced",
        random_state=42,
    )

    print(f"\nDang train model SVM (balanced) | CV Strategy: {cv_strategy}...")
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)

    # Fit StandardScaler rieng trong moi fold qua Pipeline de khong ro ri thong ke
    cv_pipe = make_pipeline(
        StandardScaler(),
        SVC(
            kernel="rbf",
            probability=True,
            C=10,
            gamma="scale",
            class_weight="balanced",
            random_state=42,
        ),
    )
    cv_scores = (
        cross_val_score(cv_pipe, X, y, cv=cv, groups=groups, scoring="f1_macro")
        if has_groups
        else cross_val_score(cv_pipe, X, y, cv=cv, scoring="f1_macro")
    )

    print("\n===== KET QUA =====")
    print(f"CV Strategy: {cv_strategy}")
    print(f"Test Accuracy: {accuracy * 100:.2f}%")
    print(f"CV Macro-F1: {cv_scores.mean() * 100:.2f}% (+/- {cv_scores.std() * 100:.2f}%)")
    print("\n===== CLASSIFICATION REPORT =====")
    print(classification_report(y_test, y_pred, target_names=["Tinh tao (0)", "Met/Ngap (1)", "Buon ngu (2)"]))
    print("===== CONFUSION MATRIX =====")
    print(confusion_matrix(y_test, y_pred))

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    meta = {
        "dataset_mode": dataset_mode,
        "features": feature_cols,
        "cv_strategy": cv_strategy,
        "num_samples": int(len(df)),
        "label_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "test_accuracy": round(float(accuracy) * 100, 2),
        "cv_macro_f1": round(float(cv_scores.mean()) * 100, 2),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nDa luu model -> {MODEL_PATH}")
    print(f"Da luu scaler -> {SCALER_PATH}")
    print(f"Da luu metadata -> {META_PATH}")


if __name__ == "__main__":
    train()
