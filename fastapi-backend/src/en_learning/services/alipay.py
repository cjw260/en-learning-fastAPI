from __future__ import annotations

import base64
import json
import textwrap
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from en_learning.common.config import Settings


def _pem(value: str, label: str) -> bytes:
    value = value.strip().replace("\\n", "\n")
    if "-----BEGIN" in value:
        return value.encode()
    body = "\n".join(textwrap.wrap(value, 64))
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----\n".encode()


def signature_content(parameters: dict[str, str]) -> str:
    return "&".join(
        f"{key}={parameters[key]}"
        for key in sorted(parameters)
        if key not in {"sign", "sign_type"} and parameters[key] != ""
    )


class AlipayGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _private_key(self) -> rsa.RSAPrivateKey:
        key = serialization.load_pem_private_key(
            _pem(self.settings.alipay_private_key.get_secret_value(), "PRIVATE KEY"),
            password=None,
        )
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Alipay private key must be RSA")
        return key

    def _public_key(self) -> rsa.RSAPublicKey:
        key = serialization.load_pem_public_key(
            _pem(self.settings.alipay_public_key.get_secret_value(), "PUBLIC KEY")
        )
        if not isinstance(key, rsa.RSAPublicKey):
            raise ValueError("Alipay public key must be RSA")
        return key

    def sign(self, content: str) -> str:
        signature = self._private_key().sign(
            content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode()

    def verify_notification(self, parameters: dict[str, str]) -> bool:
        if parameters.get("sign_type") != "RSA2":
            return False
        try:
            signature = base64.b64decode(parameters["sign"], validate=True)
            self._public_key().verify(
                signature,
                signature_content(parameters).encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (KeyError, ValueError, InvalidSignature):
            return False
        return True

    def page_pay_url(
        self,
        *,
        out_trade_no: str,
        amount: str,
        subject: str,
        body: str,
        expires_at: datetime,
    ) -> str:
        local_expiry = expires_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(
            ZoneInfo("Asia/Shanghai")
        )
        parameters = {
            "app_id": self.settings.alipay_app_id,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": f"{str(self.settings.alipay_notify_url).rstrip('/')}/api/v1/pay/notify",
            "return_url": f"{str(self.settings.alipay_notify_url).rstrip('/')}/",
            "biz_content": json.dumps(
                {
                    "out_trade_no": out_trade_no,
                    "total_amount": amount,
                    "subject": subject,
                    "body": body,
                    "product_code": "FAST_INSTANT_TRADE_PAY",
                    "time_expire": local_expiry.strftime("%Y-%m-%d %H:%M:%S"),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }
        parameters["sign"] = self.sign(signature_content(parameters))
        return f"{self.settings.alipay_gateway!s}?{urlencode(parameters)}"
