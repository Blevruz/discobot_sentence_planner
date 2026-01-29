# chatbot/middle_modules/_llm_service/dispatcher.py
from middle_modules._llm_service.protocol import validate_command, make_response, make_event

class CommandDispatcher:
    def __init__(self, context_store, generator):
        self.ctx = context_store
        self.gen = generator

    def handle(self, cmd):
        validate_command(cmd)
        op = cmd["op"]
        payload = cmd["payload"]

        if op == "APPEND":
            self.ctx.append_messages(payload["messages"])
            return [make_response(cmd["id"])]

        if op == "QUERY":
            data = self.ctx.query(**payload)
            return [make_response(cmd["id"], result={"messages": data, "version": self.ctx.version})]

        if op == "GENERATE":
            context_snapshot = self.ctx.query()
            events = []
            full = ""
            for token in self.gen.stream_generate(context_snapshot):
                full += token
                events.append(make_event("token", {"text": token}))
            self.ctx.append_messages([{"role": "assistant", "content": full}])
            events.append(make_event("generation_done", {"text": full}))
            return events

