"""
Skolaz v2.0 — Socket.IO Event Handlers
Real-time: notifications, advisor chat, application updates
"""
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from app.extensions import socketio


# ── Connection Lifecycle ──────────────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    """Client connected. Join their personal notification room."""
    if current_user.is_authenticated:
        room = f"user_{current_user.id}"
        join_room(room)
        emit("connected", {"status": "ok", "room": room})


@socketio.on("disconnect")
def handle_disconnect():
    """Client disconnected."""
    pass


# ── Advisor Chat ──────────────────────────────────────────────────────────────

@socketio.on("join_chat")
def handle_join_chat(data):
    """Advisor or student joins a student chat room."""
    student_id = data.get("student_id")
    if student_id:
        join_room(f"chat_{student_id}")
        emit("chat_joined", {"student_id": student_id}, room=f"chat_{student_id}")


@socketio.on("leave_chat")
def handle_leave_chat(data):
    student_id = data.get("student_id")
    if student_id:
        leave_room(f"chat_{student_id}")


@socketio.on("send_message")
def handle_send_message(data):
    """
    Relay a chat message to the student's room.
    Persist via REST; Socket.IO is for real-time delivery only.
    """
    student_id = data.get("student_id")
    if not student_id or not current_user.is_authenticated:
        return

    payload = {
        "sender_id": current_user.id,
        "sender_name": current_user.full_name,
        "sender_avatar": current_user.avatar_url,
        "message": data.get("message", ""),
        "timestamp": data.get("timestamp"),
    }
    emit("new_message", payload, room=f"chat_{student_id}")


# ── Application Updates ───────────────────────────────────────────────────────

@socketio.on("join_application")
def handle_join_application(data):
    app_id = data.get("application_id")
    if app_id:
        join_room(f"app_{app_id}")


def broadcast_stage_change(application_id: int, stage: str, changed_by: str):
    """Called from services to push real-time stage update to all watchers."""
    socketio.emit(
        "stage_changed",
        {"application_id": application_id, "stage": stage, "changed_by": changed_by},
        room=f"app_{application_id}",
    )


# ── Notifications ─────────────────────────────────────────────────────────────

def push_notification(user_id: int, title: str, body: str, notif_type: str = "info"):
    """Push a real-time notification to a specific user's room."""
    socketio.emit(
        "notification",
        {"title": title, "body": body, "type": notif_type},
        room=f"user_{user_id}",
    )
