import joblib
import numpy as np
import os


# PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

model_path = os.path.join(BASE_DIR, "model", "drowsy_model.pkl")

scaler_path = os.path.join(BASE_DIR, "model", "scaler.pkl")



# LOAD MODEL

model = None
scaler = None

try:

    if os.path.exists(model_path):

        model = joblib.load(model_path)

        print("Da load model")

    else:

        print("Khong tim thay model:")

        print(model_path)

    if os.path.exists(scaler_path):

        scaler = joblib.load(scaler_path)

        print("Da load scaler")

    else:

        print("Khong tim thay scaler:")

        print(scaler_path)

except Exception as e:

    print("Loi load model:", e)



# DỰ ĐOÁN

def predict_state(ear, mar):

    try:

        # chưa load model
        if model is None or scaler is None:

            return (0, 0)

        data = np.array([[ear, mar]])

        scaled_data = scaler.transform(data)

        prediction = model.predict(scaled_data)[0]

        confidence = round(np.max(model.predict_proba(scaled_data)) * 100, 2)

        return (int(prediction), confidence)

    except Exception as e:

        print("Predict error:", e)

        return (0, 0)
