"""
Skolaz v2.0 — Production WSGI Entry Point

Deployment targets:
  Vercel  : vercel.json routes everything here
  Render  : gunicorn -k eventlet -w 1 wsgi:application
  Railway : gunicorn -k eventlet -w 1 wsgi:application
  Heroku  : same as Render (Procfile)

Note: Socket.IO (real-time chat / notifications) requires a persistent
server (Render, Railway, Fly.io). On Vercel, serverless functions are
used and WebSocket connections are not supported — real-time features
will gracefully degrade.
"""
import os
from app import create_app
from app.extensions import socketio

env = os.environ.get("FLASK_ENV", "production")
application = create_app(env)

# Vercel / WSGI-compatible alias
app = application

# Wrap with SocketIO middleware for gunicorn (non-Vercel)
if os.environ.get("VERCEL") is None:
    application = socketio.middleware(application)
