# chatbot/utils/nao.py
import qi
import threading

# Thread safety because multiple modules may connect at once
_lock = threading.Lock()

nao_apps = {}      # key: "tcp://ip:port" → qi.Application
nao_sessions = {}  # key: "tcp://ip:port" → qi.Session


def connect(ip, port):
    """
    Returns a shared qi.Session backed by a qi.Application.
    Ensures only one app/session per robot per process.
    """
    connect_str = f"tcp://{ip}:{port}"

    with _lock:
        # Already connected
        if connect_str in nao_sessions:
            return nao_sessions[connect_str]

        # Create application (service host)
        app = qi.Application(
            ["ChatbotApp", f"--qi-url={connect_str}"]
        )
        app.start()

        session = app.session

        nao_apps[connect_str] = app
        nao_sessions[connect_str] = session

        return session


def disconnect(ip, port):
    """
    Stops the qi.Application and removes session.
    """
    connect_str = f"tcp://{ip}:{port}"

    with _lock:
        app = nao_apps.pop(connect_str, None)
        nao_sessions.pop(connect_str, None)

        if app:
            try:
                app.stop()
            except RuntimeError:
                pass


def get_session(ip, port):
    """Return session if exists, else None."""
    return nao_sessions.get(f"tcp://{ip}:{port}")


def is_connected(ip, port):
    return f"tcp://{ip}:{port}" in nao_sessions
