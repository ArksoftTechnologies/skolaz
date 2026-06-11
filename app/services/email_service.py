"""
Skolaz v2.0 — Email Service
"""
import logging
from flask import current_app, url_for
from app.extensions import db
from app.models.communication import EmailLog, EmailStatus
from app.models.user import User


def send_password_reset(user: User):
    """Generate token and send password reset email."""
    import secrets
    from datetime import datetime, timezone, timedelta
    
    # Generate token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()
    
    # Generate link
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    
    # In a real app, render a template and send via SMTP/SendGrid
    # For now, we'll just log it
    log = EmailLog(
        to_email=user.email,
        to_name=user.full_name,
        subject="Skolaz - Password Reset Request",
        template="auth/email/password_reset.html",
        body_preview=f"Click here to reset your password: {reset_url}",
        status=EmailStatus.SENT,
        provider="local"
    )
    db.session.add(log)
    db.session.commit()
    
    current_app.logger.info(f"Password reset link generated for {user.email}: {reset_url}")
    return True
