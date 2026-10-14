import json
from http.client import InvalidURL

import pytest

from etf_compass import NotificationError, send_email, send_report, send_serverchan, send_wecom_markdown


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_email_reads_credentials_from_environment_and_sends(monkeypatch):
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port, **kwargs):
            calls["server"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def login(self, user, password):
            calls["login"] = (user, password)

        def send_message(self, message):
            calls["message"] = message

    monkeypatch.setattr("etf_compass.notifications.smtplib.SMTP_SSL", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "private@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "email-key-test-only")
    monkeypatch.setenv("REPORT_TO", "recipient@example.test")
    send_email("Daily report", "No account details")
    assert calls["server"] == ("smtp.example.test", 465)
    assert calls["login"] == ("private@example.test", "email-key-test-only")
    assert calls["message"]["To"] == "recipient@example.test"


def test_email_reports_partial_recipient_rejection_without_addresses(monkeypatch):
    refused_address = "private-recipient@example.test"

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def login(self, *_):
            pass

        def send_message(self, _message):
            return {refused_address: (550, b"rejected")}

    monkeypatch.setattr("etf_compass.notifications.smtplib.SMTP_SSL", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_USER", "user@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "password-test-only")
    monkeypatch.setenv("REPORT_TO", refused_address)
    with pytest.raises(NotificationError) as exc:
        send_email("Report", "Body")
    assert refused_address not in str(exc.value)


def test_serverchan_supports_personal_wechat_without_logging_key(monkeypatch):
    key = "SCTtest1234"
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["form"] = request.data.decode()
        captured["timeout"] = timeout
        return FakeResponse({"code": 0})

    monkeypatch.setattr("etf_compass.notifications.urlopen", fake_urlopen)
    monkeypatch.setenv("SERVERCHAN_SENDKEY", key)
    send_serverchan("Daily ETF report", "## Rotation")
    assert key in captured["url"]
    assert "title=Daily+ETF+report" in captured["form"]
    assert "desp=%23%23+Rotation" in captured["form"]


def test_wecom_posts_markdown_using_runtime_webhook(monkeypatch):
    webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-only"
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse({"errcode": 0})

    monkeypatch.setattr("etf_compass.notifications.urlopen", fake_urlopen)
    monkeypatch.setenv("WECOM_BOT_WEBHOOK", webhook)
    send_wecom_markdown("## Weekly review")
    assert captured["url"] == webhook
    assert captured["payload"] == {"msgtype": "markdown", "markdown": {"content": "## Weekly review"}}


def test_wecom_rejects_malformed_secret_url_without_echoing_key(monkeypatch):
    secret = "dummy-secret-with-space"
    monkeypatch.setenv(
        "WECOM_BOT_WEBHOOK",
        f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={secret}",
    )
    with pytest.raises(NotificationError) as exc:
        send_wecom_markdown("body")
    assert secret not in str(exc.value)


def test_wecom_sanitizes_invalid_url_from_http_client(monkeypatch):
    secret = "dummysecret"
    monkeypatch.setenv(
        "WECOM_BOT_WEBHOOK",
        f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={secret}",
    )

    def fake_urlopen(*_, **__):
        raise InvalidURL(f"invalid URL containing key={secret}")

    monkeypatch.setattr("etf_compass.notifications.urlopen", fake_urlopen)
    with pytest.raises(NotificationError) as exc:
        send_wecom_markdown("body")
    assert secret not in str(exc.value)


def test_delivery_error_does_not_expose_sendkey(monkeypatch):
    key = "SCT_test_key_never_real"
    monkeypatch.setenv("SERVERCHAN_SENDKEY", key)

    def fake_urlopen(*_, **__):
        raise OSError("network unavailable")

    monkeypatch.setattr("etf_compass.notifications.urlopen", fake_urlopen)
    with pytest.raises(NotificationError) as exc:
        send_serverchan("Report", "body")
    assert key not in str(exc.value)


def test_send_report_attempts_all_requested_channels(monkeypatch):
    attempts = []

    def fail_email(*_, **__):
        attempts.append("email")
        raise NotificationError("email delivery failed")

    def success_serverchan(*_, **__):
        attempts.append("serverchan")

    monkeypatch.setattr("etf_compass.notifications.send_email", fail_email)
    monkeypatch.setattr("etf_compass.notifications.send_serverchan", success_serverchan)
    with pytest.raises(NotificationError, match="email"):
        send_report("Report", "body", channels=("email", "serverchan"))
    assert attempts == ["email", "serverchan"]
