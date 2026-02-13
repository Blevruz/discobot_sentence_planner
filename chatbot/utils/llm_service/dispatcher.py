# chatbot/utils/llm_service/dispatcher.py
from utils.llm_service.protocol import (
    validate_command, make_response, make_event
)

class CommandDispatcher:
    def __init__(self, context_store, generator):
        self.ctx = context_store
        self.gen = generator

    def handle(self, cmd):
        validate_command(cmd)

        cmd_id = cmd["id"]
        op = cmd["op"]
        payload = cmd["payload"]

        try:

            # ---------- APPEND ----------
            if op == "APPEND":
                inserted = self.ctx.append_messages(payload["messages"])
                yield make_response(cmd_id, result={
                    "inserted_ids": [m["msg_id"] for m in inserted],
                    "version": self.ctx.version
                })

            # ---------- INSERT ----------
            elif op == "INSERT":
                inserted = self.ctx.insert_after(
                    payload.get("anchor_id"),
                    payload["messages"]
                )
                yield make_response(cmd_id, result={
                    "inserted_ids": [m["msg_id"] for m in inserted],
                    "version": self.ctx.version
                })

            # ---------- DELETE ----------
            elif op == "DELETE":
                self.ctx.delete_ids(payload["ids"])
                yield make_response(cmd_id, result={
                    "version": self.ctx.version
                })

            # ---------- REPLACE ----------
            elif op == "REPLACE":
                inserted = self.ctx.replace_range(
                    payload["start_id"],
                    payload["end_id"],
                    payload["messages"]
                )
                yield make_response(cmd_id, result={
                    "inserted_ids": [m["msg_id"] for m in inserted],
                    "version": self.ctx.version
                })

            # ---------- QUERY ----------
            elif op == "QUERY":
                data = self.ctx.query(**payload)
                yield make_response(cmd_id, result={
                    "messages": data,
                    "version": self.ctx.version
                })

            # ---------- GENERATE ----------
            elif op == "GENERATE":
                context_snapshot = self.ctx.query()
                full = ""

                for token in self.gen.stream_generate(context_snapshot):
                    full += token
                    yield make_event("token", {"text": token})

                inserted = self.ctx.append_messages([
                    {"role": "assistant", "content": full}
                ])

                yield make_event("generation_done", {
                    "text": full,
                    "msg_id": inserted[0]["msg_id"],
                    "version": self.ctx.version
                })

            else:
                yield make_response(cmd_id, status="error",
                                    result={"error": f"Unknown op {op}"})

        except Exception as e:
            yield make_response(cmd_id, status="error",
                                result={"error": str(e)})
