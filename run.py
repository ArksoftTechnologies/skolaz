"""
Skolaz v2.0 — Application Entry Point
Run with: python run.py  |  or: flask run
"""
import os
from app import create_app
from app.extensions import socketio

# Determine environment from FLASK_ENV (defaults to development)
env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env == "development"

    # Use SocketIO's run() so WebSocket transport works locally
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug,
        log_output=debug,
    )
