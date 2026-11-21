import numpy as np

from database.mysql_service import hash_password, verify_password
from face_auth.embedding_service import match_embedding


def test_bcrypt_password_hashing_and_verification():
    hashed = hash_password("matkhau123")
    assert hashed.startswith("$2")

    matched, needs_upgrade = verify_password("matkhau123", hashed)
    assert matched is True
    assert needs_upgrade is False

    wrong_matched, _ = verify_password("sai_mat_khau", hashed)
    assert wrong_matched is False


def test_legacy_plaintext_password_flags_upgrade():
    matched, needs_upgrade = verify_password("123456", "123456")
    assert matched is True
    assert needs_upgrade is True


def test_face_embedding_matching_128d():
    rng = np.random.default_rng(42)
    vec_driver_1 = rng.normal(0, 0.1, size=128)
    vec_driver_2 = rng.normal(1.0, 0.1, size=128)

    known = [
        (1, vec_driver_1),
        (2, vec_driver_2),
    ]

    # Mau gan giong tai xe 1
    probe_1 = vec_driver_1 + rng.normal(0, 0.01, size=128)
    matched_id, similarity = match_embedding(probe_1, known, threshold=0.48)
    assert matched_id == 1
    assert similarity > 70.0

    # Nguoi la (xa ca 2)
    stranger = rng.normal(-2.0, 0.1, size=128)
    matched_stranger, _ = match_embedding(stranger, known, threshold=0.48)
    assert matched_stranger is None


def test_admin_api_requires_authentication():
    from backend.app import app

    client = app.test_client()

    res_drivers = client.get("/api/admin/drivers")
    assert res_drivers.status_code == 401

    res_internal = client.post(
        "/api/internal/alert-event",
        json={"type": "BUON_NGU"},
        headers={"X-Internal-Key": "wrong-key"},
    )
    assert res_internal.status_code == 401
