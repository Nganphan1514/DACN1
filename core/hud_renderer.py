import cv2


def _draw_fatigue_bar(frame, fatigue_score, x=20, y=15, width=260, height=16):
    score = max(0.0, min(100.0, float(fatigue_score)))
    cv2.rectangle(frame, (x, y), (x + width, y + height), (50, 50, 50), -1)

    fill_w = int((score / 100.0) * width)
    if score >= 65:
        bar_color = (0, 0, 255)
    elif score >= 30:
        bar_color = (0, 165, 255)
    else:
        bar_color = (0, 220, 0)

    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + height), bar_color, -1)

    cv2.rectangle(frame, (x, y), (x + width, y + height), (220, 220, 220), 1)
    cv2.putText(
        frame,
        f"Fatigue: {score:.0f}%",
        (x + width + 10, y + height - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        bar_color,
        2,
    )


def render_hud(
    frame,
    ten_tai_xe,
    auth_done,
    nguoi_lai_hop_le,
    vehicle_name,
    xe_dang_chay,
    ear,
    mar,
    blink_count,
    perclos,
    pitch,
    yaw,
    confidence,
    risk_score,
    fatigue_score,
    status,
    status_color,
    reasons,
    ai_probs,
    blink_rate_per_min,
    yawn_count_3m,
    drowsy_count,
    fps,
    runtime,
):
    _draw_fatigue_bar(frame, fatigue_score, x=20, y=12)

    reason_text = ", ".join(reasons) if reasons else "Binh thuong"
    probs_text = (
        f"AI -> Thuc: {ai_probs.get('awake', 0):.0f}% | "
        f"Met: {ai_probs.get('fatigue', 0):.0f}% | "
        f"Ngu: {ai_probs.get('drowsy', 0):.0f}%"
    )

    texts = [
        f"Trang thai: {status}",
        f"Ly do: {reason_text}",
        f"Tai xe: {ten_tai_xe} ({'HOP LE' if nguoi_lai_hop_le else 'CHUA XAC THUC'})",
        f"Xe: {vehicle_name} | {'DANG CHAY' if xe_dang_chay else 'TAM DUNG'}",
        probs_text,
        f"EAR: {ear:.2f} | MAR: {mar:.2f} | PERCLOS: {perclos:.2f}",
        f"Pitch: {pitch:.1f} | Yaw: {yaw:.1f} | Risk: {risk_score}/10",
        f"Blink/min: {blink_rate_per_min} (Tong: {blink_count}) | Ngap(3p): {yawn_count_3m}",
        f"So lan buon ngu: {drowsy_count} | FPS: {fps} | {runtime}s",
        "Phim 1: DUNG | Phim 2: CHAY | Q: THOAT",
    ]

    y = 55
    for idx, text in enumerate(texts):
        if idx == 0:
            draw_color = status_color
        elif idx == 1 and reasons:
            draw_color = status_color
        elif idx == 3:
            draw_color = (0, 255, 255) if not xe_dang_chay else (0, 255, 0)
        elif idx == len(texts) - 1:
            draw_color = (180, 220, 255)
        else:
            draw_color = (255, 255, 255)

        cv2.putText(
            frame,
            text,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            draw_color,
            2,
        )
        y += 26
