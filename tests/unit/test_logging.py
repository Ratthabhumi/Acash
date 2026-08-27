"""Unit tests for telemetry, structured JSON logging, and secret redaction."""

from acash.telemetry.logging import configure_logging, get_logger, secret_redaction_processor


def test_secret_redaction_processor() -> None:
    event_dict = {
        "event": "user_login",
        "api_key": "super_secret_key_123",
        "password": "my_password",
        "nested": {
            "token": "bearer_jwt_token_456",
            "safe_field": "visible_value",
        },
        "safe_number": 42,
    }

    processed = secret_redaction_processor(None, "info", event_dict)
    assert processed["api_key"] == "[REDACTED]"
    assert processed["password"] == "[REDACTED]"
    assert processed["nested"]["token"] == "[REDACTED]"
    assert processed["nested"]["safe_field"] == "visible_value"
    assert processed["safe_number"] == 42


def test_configure_and_get_logger() -> None:
    configure_logging(json_format=True, log_level="INFO", redact_secrets=True)
    logger = get_logger("test_acash")
    assert logger is not None
