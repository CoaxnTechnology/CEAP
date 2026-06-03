import smtplib
import time
from email.mime.text import MIMEText

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
    if not OfficeConfig.SMTP_HOST:
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = OfficeConfig.SMTP_FROM
        msg["To"] = to

        with smtplib.SMTP(OfficeConfig.SMTP_HOST, OfficeConfig.SMTP_PORT) as server:
            if OfficeConfig.SMTP_USER:
                server.starttls()
                server.login(OfficeConfig.SMTP_USER, OfficeConfig.SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False
