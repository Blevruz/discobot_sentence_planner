# chatbot/middle_modules/_llm_service/protocol.py
import uuid

class ProtocolError(Exception):
    pass


def validate_command(cmd: dict):
    required = ["id", "from", "op", "payload"]
    for r in required:
        if r not in cmd:
            raise ProtocolError(f"Missing field: {r}")

    return True


def make_response(cmd_id, status="ok", result=None):
    return {
        "type": "response",
        "id": cmd_id,
        "status": status,
        "result": result
    }


def make_event(event_type, data):
    return {
        "type": "event",
        "event": event_type,
        "data": data
    }


def new_msg_id():
    return str(uuid.uuid4())


