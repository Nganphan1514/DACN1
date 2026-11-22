from unittest.mock import MagicMock, patch

from services import expo_push_service


def test_is_valid_expo_token():
    assert expo_push_service.is_valid_expo_token("ExponentPushToken[abc123]") is True
    assert expo_push_service.is_valid_expo_token("ExpoPushToken[xyz789]") is True
    assert expo_push_service.is_valid_expo_token("invalid-token") is False
    assert expo_push_service.is_valid_expo_token("") is False


def test_send_expo_push_messages_posts_valid_batch():
    fake_resp = MagicMock()
    fake_resp.status_code = 200

    with patch("services.expo_push_service.requests.post", return_value=fake_resp) as mock_post:
        ok = expo_push_service.send_expo_push_messages(
            tokens=["ExponentPushToken[token1]", "bad_token", "ExpoPushToken[token2]"],
            title="Cảnh báo BUỒN NGỦ",
            body="Tài xế Nguyễn Văn An có dấu hiệu buồn ngủ",
            data={"type": "BUON_NGU"},
        )
        assert ok is True
        mock_post.assert_called_once()
        sent_payload = mock_post.call_args.kwargs["json"]
        assert len(sent_payload) == 2
        assert sent_payload[0]["to"] == "ExponentPushToken[token1]"
        assert sent_payload[0]["channelId"] == "alerts"
        assert sent_payload[1]["to"] == "ExpoPushToken[token2]"
