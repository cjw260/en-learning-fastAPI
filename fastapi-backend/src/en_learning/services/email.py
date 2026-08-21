from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from en_learning.common.config import Settings


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_html(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        message_id: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message["Message-ID"] = f"<{message_id}@en-learning>"
        message.set_content("请使用支持 HTML 的邮件客户端查看学习摘要。")
        message.add_alternative(html, subtype="html")
        await asyncio.to_thread(self._send, message)

    def _send(self, message: EmailMessage) -> None:
        timeout = float(self.settings.worker_job_timeout_seconds)
        if self.settings.email_use_ssl:
            with smtplib.SMTP_SSL(
                self.settings.email_host,
                self.settings.email_port,
                timeout=timeout,
                context=ssl.create_default_context(),
            ) as client:
                client.login(
                    self.settings.email_user,
                    self.settings.email_password.get_secret_value(),
                )
                client.send_message(message)
            return
        with smtplib.SMTP(
            self.settings.email_host,
            self.settings.email_port,
            timeout=timeout,
        ) as client:
            if self.settings.email_starttls:
                client.starttls(context=ssl.create_default_context())
            client.login(
                self.settings.email_user,
                self.settings.email_password.get_secret_value(),
            )
            client.send_message(message)
