# chatbot/utils/nao.py
import qi
import threading
import utils.config

_lock = threading.Lock()
nao_sessions = {}  # Key: "tcp://ip:port" → qi.Session
retries = 10

def connect(ip, port):
    connect_str = f"tcp://{ip}:{port}"
    utils.config.debug_print(f"[nao] Connecting to {connect_str}")

    with _lock:
        if connect_str in nao_sessions:
            return nao_sessions[connect_str]
        
        session = qi.Session()

        for i in range(retries):
            try:
                session.connect(connect_str)
                break
            except Exception as e:
                utils.config.debug_print(f"[nao] Error connecting to NAO at {connect_str}:{e} (attempt {i}/{retries})")

        nao_sessions[connect_str] = session
        return session

def disconnect(ip, port):
    connect_str = f"tcp://{ip}:{port}"
    with _lock:
        session = nao_sessions.pop(connect_str, None)
        if session:
            try:
                session.close()
            except RuntimeError:
                pass

def get_session(ip, port):
    return nao_sessions.get(f"tcp://{ip}:{port}")

def is_connected(ip, port):
    return f"tcp://{ip}:{port}" in nao_sessions

