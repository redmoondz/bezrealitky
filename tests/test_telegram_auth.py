import hashlib
import hmac
import json
import time
from unittest import TestCase
from urllib.parse import urlencode

from webapp.backend.telegram_auth import validate_init_data

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def _signed_init_data(bot_token: str, auth_date: int, user: dict) -> str:
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAFakeQueryId",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


class ValidateInitDataTests(TestCase):
    def test_accepts_a_correctly_signed_payload(self):
        init_data = _signed_init_data(BOT_TOKEN, int(time.time()), {"id": 42, "first_name": "Ada"})
        pairs = validate_init_data(init_data, BOT_TOKEN)
        self.assertIn("user", pairs)

    def test_rejects_a_tampered_hash(self):
        init_data = _signed_init_data(BOT_TOKEN, int(time.time()), {"id": 42, "first_name": "Ada"})
        tampered = init_data.replace("hash=", "hash=deadbeef", 1)
        with self.assertRaises(ValueError):
            validate_init_data(tampered, BOT_TOKEN)

    def test_rejects_a_payload_signed_with_a_different_bot_token(self):
        init_data = _signed_init_data(BOT_TOKEN, int(time.time()), {"id": 42, "first_name": "Ada"})
        with self.assertRaises(ValueError):
            validate_init_data(init_data, "different-token")

    def test_rejects_a_stale_auth_date(self):
        stale = int(time.time()) - 25 * 3600
        init_data = _signed_init_data(BOT_TOKEN, stale, {"id": 42, "first_name": "Ada"})
        with self.assertRaises(ValueError):
            validate_init_data(init_data, BOT_TOKEN)

    def test_rejects_empty_init_data(self):
        with self.assertRaises(ValueError):
            validate_init_data("", BOT_TOKEN)
