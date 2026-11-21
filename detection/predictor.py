import json
import os

import joblib
import numpy as np


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "drowsy_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "model", "scaler.pkl")
META_PATH = os.path.join(BASE_DIR, "model", "model_meta.json")

model = None
scaler = None
expected_features = ["EAR", "MAR"]


def _load_artifacts():
    global model, scaler, expected_features
    try:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            print("Da load model")
        else:
            print("Khong tim thay model:", MODEL_PATH)

        if os.path.exists(SCALER_PATH):
            scaler = joblib.load(SCALER_PATH)
            print("Da load scaler")
        else:
            print("Khong tim thay scaler:", SCALER_PATH)

        if os.path.exists(META_PATH):
            with open(META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                if isinstance(meta.get("features"), list) and meta["features"]:
                    expected_features = meta["features"]
        elif scaler is not None and hasattr(scaler, "n_features_in_"):
            if scaler.n_features_in_ == 5:
                expected_features = ["EAR", "MAR", "Pitch", "Yaw", "PERCLOS"]
            else:
                expected_features = ["EAR", "MAR"]
    except Exception as e:
        print("Loi load model:", e)


_load_artifacts()


def _build_feature_vector(ear, mar, pitch=0.0, yaw=0.0, perclos=0.0):
    mapping = {
        "EAR": float(ear),
        "MAR": float(mar),
        "Pitch": float(pitch),
        "Yaw": float(yaw),
        "PERCLOS": float(perclos),
    }
    row = [mapping.get(name, 0.0) for name in expected_features]
    return np.array([row], dtype=np.float64)


def predict_proba_dict(ear, mar, pitch=0.0, yaw=0.0, perclos=0.0):
    """
    Tra ve day du du doan va xac suat 3 lop:
    {
        "prediction": 0 | 1 | 2,
        "confidence": float (0..100),
        "probs": {0: p_awake, 1: p_fatigue, 2: p_drowsy}
    }
    """
    default_result = {
        "prediction": 0,
        "confidence": 0.0,
        "probs": {0: 1.0, 1: 0.0, 2: 0.0},
    }

    try:
        if model is None or scaler is None:
            return default_result

        data = _build_feature_vector(ear, mar, pitch, yaw, perclos)
        scaled_data = scaler.transform(data)

        proba_arr = model.predict_proba(scaled_data)[0]
        classes = [int(c) for c in model.classes_]
        probs = {0: 0.0, 1: 0.0, 2: 0.0}
        for cls_id, prob in zip(classes, proba_arr):
            if cls_id in probs:
                probs[cls_id] = float(prob)

        best_idx = int(np.argmax(proba_arr))
        prediction = classes[best_idx]
        confidence = round(float(proba_arr[best_idx]) * 100.0, 2)

        return {
            "prediction": prediction,
            "confidence": confidence,
            "probs": probs,
        }

    except Exception as e:
        print("Predict error:", e)
        return default_result


def predict_state(ear, mar, pitch=0.0, yaw=0.0, perclos=0.0):
    """
    Giu tuong thich nguoc: tra ve (prediction, confidence).
    """
    res = predict_proba_dict(ear, mar, pitch, yaw, perclos)
    return (res["prediction"], res["confidence"])
