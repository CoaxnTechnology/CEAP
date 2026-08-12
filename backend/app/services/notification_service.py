import smtplib
from email.mime.text import MIMEText
from sqlalchemy import event

from app.db import SessionLocal
from app.models import Notification
from app.config import OfficeConfig


def create_notification(
    user_email: str,
    notif_type: str,
    title: str = "",
    message: str = "",
    link: str = "",
) -> dict:
    db = SessionLocal()
    try:
        notif = Notification(
            user_email=user_email,
            type=notif_type,
            title=title,
            message=message,
            link=link,
        )
        db.add(notif)
        db.commit()
        return {"id": notif.id, "created": True}
    finally:
        db.close()


def get_unread_count(user_email: str) -> int:
    db = SessionLocal()
    try:
        return db.query(Notification).filter(
            Notification.user_email == user_email,
            Notification.read == 0,
        ).count()
    finally:
        db.close()


def get_notifications(user_email: str, limit: int = 20) -> list:
    db = SessionLocal()
    try:
        notifs = (
            db.query(Notification)
            .filter(Notification.user_email == user_email)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "link": n.link,
                "read": bool(n.read),
                "created_at": n.created_at,
            }
            for n in notifs
        ]
    finally:
        db.close()


def mark_as_read(notification_id: str, user_email: str) -> bool:
    db = SessionLocal()
    try:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_email == user_email,
        ).first()
        if not notif:
            return False
        notif.read = 1
        db.commit()
        return True
    finally:
        db.close()


def send_email(to: str, subject: str, body: str) -> bool:
    if not OfficeConfig.SMTP_PASS:
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = OfficeConfig.SMTP_FROM
        msg["To"] = to

        with smtplib.SMTP(OfficeConfig.SMTP_HOST, OfficeConfig.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(OfficeConfig.SMTP_USER, OfficeConfig.SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False


def send_invite_email(email: str, role: str, temp_password: str, school_name: str = "") -> bool:
    body = (
        f"You have been invited to join {school_name or 'CEAP'} as {role}.\n\n"
        f"Your login details:\nEmail: {email}\nTemporary password: {temp_password}\n\n"
        "Sign in at https://ceap.coaxn.com and change your password once you log in."
    )
    return send_email(email, "You're invited to CEAP", body)


def _mirror_notification_email(mapper, connection, target):
    # ponytail: only the DB notification; HR leave approval emails ride on
    # the existing Notification rows and need no separate hook
    send_email(
        target.user_email,
        target.title or "CEAP notification",
        target.message or "",
    )


event.listen(Notification, "after_insert", _mirror_notification_email)
