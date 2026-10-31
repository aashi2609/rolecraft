"""Email service with provider abstraction: console | smtp | resend."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_password_reset_email(user_email: str, reset_token: str) -> bool:
    """Send password reset email. Returns True if sent, False if failed."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    if EMAIL_PROVIDER == "console":
        logger.info(f"[DEV] Password reset link for {user_email}: {reset_link}")
        return True
    
    elif EMAIL_PROVIDER == "resend":
        try:
            import resend
            resend.api_key = os.getenv("RESEND_API_KEY")
            resend.Emails.send(dict(
                to=user_email,
                from_="noreply@rolecraft.dev",
                subject="Reset your RoleCraft password",
                html=f"""
                <p>You requested a password reset for your RoleCraft account.</p>
                <p><a href="{reset_link}">Reset Password</a></p>
                <p>This link expires in 1 hour. If you didn't request this, ignore it.</p>
                """
            ))
            logger.info(f"Resend: password reset sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Resend error: {e}")
            return False
    
    elif EMAIL_PROVIDER == "smtp":
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASSWORD")
            
            msg = MIMEText(f"Reset link: {reset_link}\n\nExpires in 1 hour. Ignore if not requested.")
            msg["Subject"] = "Reset your RoleCraft password"
            msg["From"] = smtp_user
            msg["To"] = user_email
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            logger.info(f"SMTP: password reset sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False
    
    else:
        logger.error(f"Unknown EMAIL_PROVIDER: {EMAIL_PROVIDER}")
        return False
