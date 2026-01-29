# chatbot/middle_modules/_llm_service/context_store.py
from middle_modules._llm_service.protocol import new_msg_id

class ContextStore:
    def __init__(self, initial_context=None):
        self.messages = []
        self.version = 0

        if initial_context:
            self.append_messages(initial_context)

    def _bump_version(self):
        self.version += 1

    def _prepare_messages(self, messages):
        out = []
        for m in messages:
            m = m.copy()
            m["msg_id"] = new_msg_id()
            m.setdefault("meta", {})
            out.append(m)
        return out

    # ---------- APPEND ----------
    def append_messages(self, messages):
        new_msgs = self._prepare_messages(messages)
        self.messages.extend(new_msgs)
        self._bump_version()
        return new_msgs

    # ---------- INSERT ----------
    def insert_after(self, anchor_id, messages):
        new_msgs = self._prepare_messages(messages)

        if anchor_id is None:
            # insert at beginning
            self.messages = new_msgs + self.messages
            self._bump_version()
            return new_msgs

        idx = next((i for i, m in enumerate(self.messages) if m["msg_id"] == anchor_id), None)
        if idx is None:
            raise ValueError("Anchor ID not found")

        for m in reversed(new_msgs):
            self.messages.insert(idx + 1, m)

        self._bump_version()
        return new_msgs

    # ---------- DELETE ----------
    def delete_ids(self, ids):
        before = len(self.messages)
        self.messages = [m for m in self.messages if m["msg_id"] not in ids]
        if len(self.messages) != before:
            self._bump_version()

    # ---------- REPLACE ----------
    def replace_range(self, start_id, end_id, messages):
        start = next((i for i, m in enumerate(self.messages) if m["msg_id"] == start_id), None)
        end = next((i for i, m in enumerate(self.messages) if m["msg_id"] == end_id), None)

        if start is None or end is None:
            raise ValueError("Start or end ID not found")

        if start > end:
            start, end = end, start

        del self.messages[start:end+1]

        anchor = self.messages[start-1]["msg_id"] if start > 0 else None
        inserted = self.insert_after(anchor, messages)
        return inserted

    # ---------- QUERY ----------
    def query(self, mode="all", filter=None):
        if mode == "all":
            return self.messages.copy()
        return []
