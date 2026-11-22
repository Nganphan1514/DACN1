from unittest.mock import MagicMock, patch

from services import storage_service


def test_resolve_snapshot_url_handles_cloud_and_local_paths():
    cloud = "https://abc.supabase.co/storage/v1/object/public/snapshots/drowsy_1.jpg"
    assert storage_service.resolve_snapshot_url(cloud) == cloud

    local = r"D:\PROJECT\DACN1\snapshots\drowsy_20261122.jpg"
    assert storage_service.resolve_snapshot_url(local) == "/api/snapshots/drowsy_20261122.jpg"

    assert storage_service.resolve_snapshot_url(None) is None


def test_upload_snapshot_falls_back_when_not_configured(tmp_path):
    img = tmp_path / "test_snap.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")

    with patch.object(storage_service, "SUPABASE_URL", ""), patch.object(
        storage_service, "SUPABASE_SERVICE_KEY", ""
    ):
        result = storage_service.upload_snapshot_to_supabase(str(img))
        assert result == str(img)


def test_upload_snapshot_returns_public_url_on_success(tmp_path):
    img = tmp_path / "drowsy_ok.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")

    fake_resp = MagicMock()
    fake_resp.status_code = 200

    with patch.object(storage_service, "SUPABASE_URL", "https://demo.supabase.co"), patch.object(
        storage_service, "SUPABASE_SERVICE_KEY", "secret-service-key"
    ), patch.object(storage_service, "SUPABASE_SNAPSHOT_BUCKET", "snapshots"), patch(
        "services.storage_service.requests.post", return_value=fake_resp
    ) as mock_post:
        result = storage_service.upload_snapshot_to_supabase(str(img))
        assert (
            result
            == "https://demo.supabase.co/storage/v1/object/public/snapshots/drowsy_ok.jpg"
        )
        mock_post.assert_called_once()
