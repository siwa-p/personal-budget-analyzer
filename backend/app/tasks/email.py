import asyncio

from fastapi_mail import FastMail, MessageSchema

from app.core.celery_app import celery_app
from app.core.email import get_mail_config


def _send_email(to_email: str, subject: str, body_html: str) -> None:
    config = get_mail_config()
    fm = FastMail(config)
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=body_html,
        subtype="html",
    )
    asyncio.run(fm.send_message(message))


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(to_email: str, reset_url: str) -> None:
    subject = "Password reset request"
    body_html = (
        "<p>We received a request to reset your password.</p>"
        "<p>Click the link below to set a new password:</p>"
        f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )
    _send_email(to_email=to_email, subject=subject, body_html=body_html)
