from core.drowsiness_analyzer import DrowsinessAnalyzer
from detection.eye_calibration import EyeCalibration
from detection.feature_extractor import calculate_ear, calculate_mar
from detection.predictor import predict_proba_dict


def test_calculate_ear_open_vs_closed():
    open_eye = [(0, 10), (3, 14), (7, 14), (10, 10), (7, 6), (3, 6)]
    closed_eye = [(0, 10), (3, 10.5), (7, 10.5), (10, 10), (7, 9.5), (3, 9.5)]

    ear_open = calculate_ear(open_eye)
    ear_closed = calculate_ear(closed_eye)

    assert ear_open > 0.30
    assert ear_closed < 0.15


def test_calculate_mar_closed_vs_yawn():
    closed_mouth = [(0, 10), (5, 11), (10, 10), (5, 9)]
    yawn_mouth = [(0, 10), (5, 18), (10, 10), (5, 2)]

    assert calculate_mar(closed_mouth) < 0.3
    assert calculate_mar(yawn_mouth) > 1.0


def test_eye_calibration_normalizes_small_eyes():
    cal = EyeCalibration(duration=0.0, reference_ear=0.30, min_samples=5)
    for _ in range(5):
        cal.update(0.20, 0.20)

    assert cal.ready is True
    assert abs(cal.normalize_ear(0.20, 0.20) - 0.30) < 0.01
    assert cal.normalize_ear(0.10, 0.10) < 0.20


def test_drowsiness_analyzer_confirms_drowsy_after_threshold():
    analyzer = DrowsinessAnalyzer(
        ear_threshold=0.20,
        drowsy_threshold=5,
        drowsy_confirm_time=1.0,
    )

    t = 1000.0
    result = None
    for i in range(6):
        result = analyzer.update(ear=0.14, mar=0.2, pitch=0.0, now=t + i * 0.3)

    assert result["status"] == "BUON NGU"
    assert result["is_real_drowsy"] is True
    assert "NHAM MAT LAU" in result["reasons"]
    assert result["fatigue_score"] >= 70.0
    assert result["drowsy_count"] == 1


def test_drowsiness_analyzer_ignores_brief_blink():
    analyzer = DrowsinessAnalyzer(
        ear_threshold=0.20,
        drowsy_threshold=25,
        drowsy_confirm_time=1.2,
    )

    t = 2000.0
    for i in range(3):
        result = analyzer.update(ear=0.14, mar=0.2, pitch=0.0, now=t + i * 0.05)

    assert result["status"] == "TINH TAO"
    assert result["is_real_drowsy"] is False
    assert result["blink_count"] == 1


def test_drowsiness_analyzer_detects_distraction_from_yaw():
    analyzer = DrowsinessAnalyzer(yaw_limit=25.0, distraction_confirm_time=2.0)

    t = 3000.0
    result = None
    for i in range(6):
        result = analyzer.update(ear=0.30, mar=0.10, pitch=0.0, yaw=32.0, now=t + i * 0.5)

    assert result["status"] == "MAT TAP TRUNG"
    assert result["is_distracted"] is True
    assert "MAT TAP TRUNG" in result["reasons"]


def test_drowsiness_analyzer_yawn_frequency_triggers_fatigue():
    analyzer = DrowsinessAnalyzer(mar_threshold=0.65, yawn_confirm_time=0.8)

    t = 4000.0
    # Ngap lan 1 (keo dai 1.0s)
    for i in range(5):
        analyzer.update(ear=0.28, mar=0.80, pitch=0.0, now=t + i * 0.25)
    # Khep mieng
    analyzer.update(ear=0.28, mar=0.10, pitch=0.0, now=t + 2.0)
    # Ngap lan 2 (keo dai 1.0s)
    result = None
    for i in range(5):
        result = analyzer.update(ear=0.28, mar=0.82, pitch=0.0, now=t + 5.0 + i * 0.25)

    assert result["yawn_count_3m"] == 2
    assert result["status"] == "MET MOI"
    assert "NGAP LIEN TUC" in result["reasons"]


def test_fatigue_score_decays_gradually_when_alert():
    analyzer = DrowsinessAnalyzer(
        ear_threshold=0.20,
        drowsy_threshold=5,
        drowsy_confirm_time=1.0,
    )

    t = 5000.0
    for i in range(6):
        analyzer.update(ear=0.12, mar=0.10, pitch=0.0, now=t + i * 0.3)

    peak = analyzer.fatigue_score
    assert peak >= 70.0

    # Mo mat 1 frame -> khong tut ve 0 ngay lap tuc ma giam tu tu
    after_one = analyzer.update(ear=0.32, mar=0.10, pitch=0.0, now=t + 2.5)
    assert 0.0 < after_one["fatigue_score"] < peak


def test_predict_proba_dict_returns_valid_3_class_probabilities():
    out = predict_proba_dict(ear=0.30, mar=0.05)
    assert out["prediction"] in (0, 1, 2)
    assert abs(sum(out["probs"].values()) - 1.0) < 0.02
