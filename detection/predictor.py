import joblib
import numpy as np

model = joblib.load(
    "ai/model/drowsy_model.pkl"
)


def predict_state(
    ear,
    mar
):

    data = np.array([
        [ear, mar]
    ])

    prediction = (
        model.predict(data)[0]
    )

    return prediction