"""Optional SMTP, Server酱, and WeCom delivery using runtime-only secrets."""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
from collections.abc import Sequence
from email.message import EmailMessage
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


class NotificationError(RuntimeError):
    """A delivery failure with credential-safe error text."""


def _post_form(url: str, values: dict[str, str], *, service: str) -> dict[str, object]:
    request = Request(url, data=urlencode(values).encode(), method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError, ValueError) as exc:
        code = getattr(exc, "code", None)
        suffix = f" (HTTP {code})" if code else ""
        raise NotificationError(f"{service} delivery failed{suffix}") from None
    if not isinstance(result, dict):
        raise NotificationError(f"{service} returned an invalid response")
    return result


def send_email(subject: str, body: str, *, html_body: str | None = None) -> None:
    """Send a report over SMTP_SSL using environment variables.

    Required: ``SMTP_HOST``, ``SMTP_USER``, ``SMTP_PASSWORD``, ``REPORT_TO``.
    Optional: ``SMTP_PORT`` (defaults to 465), ``REPORT_FROM`` (defaults to
    ``SMTP_USER``). Credentials and recipient addresses are never included in
    returned values or raised error messages.
    """
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_TO")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise NotificationError(f"email configuration is missing: {', '.join(missing)}")
    try:
        port = int(os.environ.get("SMTP_PORT", "465"))
    except ValueError:
        raise NotificationError("SMTP_PORT must be an integer") from None

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ.get("REPORT_FROM", os.environ["SMTP_USER"])
    message["To"] = os.environ["REPORT_TO"]
    message.set_content(body)
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP_SSL(
            os.environ["SMTP_HOST"], port, timeout=20,
            context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            refused = smtp.send_message(message)
            if refused:
                raise NotificationError("email delivery failed (one or more recipients were refused)")
    except NotificationError:
        raise
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        code = getattr(exc, "smtp_code", None)
        suffix = f" (SMTP {code})" if code else ""
        raise NotificationError(f"email delivery failed{suffix}") from None


def _serverchan_url(sendkey: str) -> str:
    if sendkey.startswith("sctp"):
        match = re.fullmatch(r"sctp(\d+)t[A-Za-z0-9]+", sendkey)
        if not match:
            raise NotificationError("Server酱 SendKey has an invalid format")
        uid = match.group(1)
        return f"https://{uid}.push.ft07.com/send/{sendkey}.send"
    if re.fullmatch(r"SCT[A-Za-z0-9]+", sendkey):
        return f"https://sctapi.ftqq.com/{sendkey}.send"
    raise NotificationError("Server酱 SendKey must use a supported SCT or sctp format")


def send_serverchan(title: str, body: str) -> None:
    """Push Markdown to a linked WeChat account through Server酱.

    Reads ``SERVERCHAN_SENDKEY`` at call time. The SendKey is part of the
    HTTPS path and is never returned, logged, or included in error messages.
    """
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "")
    if not sendkey:
        raise NotificationError("Server酱 configuration is missing: SERVERCHAN_SENDKEY")
    if "\n" in title or "\r" in title:
        raise ValueError("title must be a single line")
    result = _post_form(
        _serverchan_url(sendkey), {"title": title, "desp": body}, service="Server酱"
    )
    if result.get("code") != 0:
        raise NotificationError("Server酱 rejected the message")


def send_wecom_markdown(body: str) -> None:
    """Push Markdown to an enterprise WeChat group robot.

    Reads the full secret URL from ``WECOM_BOT_WEBHOOK`` at call time.
    """
    webhook = os.environ.get("WECOM_BOT_WEBHOOK", "")
    if not webhook:
        raise NotificationError("WeCom configuration is missing: WECOM_BOT_WEBHOOK")
    parsed = urlsplit(webhook)
    if (
        any(character.isspace() or ord(character) < 32 for character in webhook)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.scheme != "https"
        or parsed.hostname != "qyapi.weixin.qq.com"
        or parsed.path != "/cgi-bin/webhook/send"
        or bool(parsed.fragment)
        or not parse_qs(parsed.query).get("key")
    ):
        raise NotificationError("WeCom Webhook URL has an invalid format")
    try:
        request = Request(
            webhook,
            data=json.dumps({"msgtype": "markdown", "markdown": {"content": body}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError, ValueError) as exc:
        code = getattr(exc, "code", None)
        suffix = f" (HTTP {code})" if code else ""
        raise NotificationError(f"WeCom delivery failed{suffix}") from None
    if not isinstance(result, dict) or result.get("errcode") != 0:
        raise NotificationError("WeCom rejected the message")


def send_report(
    subject: str,
    body: str,
    *,
    html_body: str | None = None,
    channels: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Attempt each requested channel and raise without exposing secrets.

    Supported channels are ``email``, ``serverchan`` (personal WeChat via
    Server酱), and ``wecom`` (enterprise WeChat group robot).
    """
    senders = {
        "email": lambda: send_email(subject, body, html_body=html_body),
        "serverchan": lambda: send_serverchan(subject, body),
        "wecom": lambda: send_wecom_markdown(body),
    }
    if channels is None:
        configured = []
        if all(os.environ.get(name) for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_TO")):
            configured.append("email")
        if os.environ.get("SERVERCHAN_SENDKEY"):
            configured.append("serverchan")
        if os.environ.get("WECOM_BOT_WEBHOOK"):
            configured.append("wecom")
        channels = configured
    if not channels:
        raise NotificationError("no notification channels are configured")
    if len(set(channels)) != len(channels):
        raise ValueError("notification channels must be unique")
    unsupported = sorted(set(channels) - set(senders))
    if unsupported:
        raise ValueError(f"unsupported notification channel(s): {', '.join(unsupported)}")
    failures: list[str] = []
    sent: list[str] = []
    for channel in channels:
        try:
            senders[channel]()
            sent.append(channel)
        except NotificationError:
            failures.append(channel)
    if failures:
        details = f"; sent: {', '.join(sent)}" if sent else ""
        raise NotificationError(f"delivery failed for: {', '.join(failures)}{details}")
    return tuple(sent)
