# chatbot/middle_modules/_llm_service/context_store.py
from middle_modules._llm_service.protocol import new_msg_id

class ContextStore:
    def __init__(self, initial_context=None):
        self.messages = []
        self.version = 0

        if initial_context:
            for m in initial_context:
                self.append_messages([m])

    def _bump_version(self):
        self.version += 1

    def append_messages(self, messages):
        for m in messages:
            m = m.copy()
            m["msg_id"] = new_msg_id()
            m.setdefault("meta", {})
            self.messages.append(m)
        self._bump_version()

    def insert_after(self, anchor_id, messages):
        idx = next((i for i, m in enumerate(self.messages) if m["msg_id"] == anchor_id), None)
        if idx is None:
            raise ValueError("Anchor ID not found")

        for m in messages:
            m = m.copy()
            m["msg_id"] = new_msg_id()
            self.messages.insert(idx + 1, m)
            idx += 1
        self._bump_version()

    def delete_ids(self, ids):
        self.messages = [m for m in self.messages if m["msg_id"] not in ids]
        self._bump_version()

    def replace_range(self, start_id, end_id, messages):
        start = next(i for i, m in enumerate(self.messages) if m["msg_id"] == start_id)
        end = next(i for i, m in enumerate(self.messages) if m["msg_id"] == end_id)
        del self.messages[start:end+1]
        anchor = self.messages[start-1]["msg_id"] if start > 0 else None
        self.insert_after(anchor, messages)

    def query(self, mode="all", filter=None):
        if mode == "all":
            return self.messages.copy()
        # extend later

