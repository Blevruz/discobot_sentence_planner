# chatbot/middle_modules/woz_handler.py
import uuid
import json
from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
import utils.config

middle_modules_class = {}

class WoZHandler(DummyModule):
    """
    Wizard of Oz Handler
    Routes WoZ interface messages to appropriate destinations:
    - system_prompt: sends as system message to LLM
    - assistant_speech: sends as assistant message to LLM AND to TTS for speaking
    - regular strings: passes through as system messages (for backward compatibility)
    """
    
    def __init__(self, name="woz_handler", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'
        
        self._input_queues['input'] = QueueSlot(self, 'input', datatype='any')
        
        self._output_queues['system_cmd'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['assistant_cmd'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['speech_text'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['passthrough_text'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['user_text'] = QueueSlot(self, 'output', datatype='string')

    def action(self, i):
        if len(self._input_queues['input']) > 0:
            data = self._input_queues['input'].get()
            if data is not None:
                utils.config.debug_print(f"[{self.name}] Received data: {data}")
                
                # If it's a simple string, pass it through for backward compatibility
                if isinstance(data, str):
                    # Try to parse as JSON first
                    try:
                        parsed_data = json.loads(data)
                        data = parsed_data
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, just a regular string - pass through
                        utils.config.debug_print(f"[{self.name}] Passing through string: {data}")
                        self._output_queues['passthrough_text'].put(data)
                        return
                
                # Parse bytes as JSON
                if isinstance(data, bytes):
                    try:
                        data = json.loads(data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        utils.config.debug_print(f"[{self.name}] Failed to parse bytes: {data}")
                        return
                
                # Handle dict/parsed JSON
                if isinstance(data, dict):
                    message_type = data.get("type")
                    content = data.get("content", "")
                    
                    # Check for user message from webpages
                    if "userMessage" in data:
                        user_message = data.get("userMessage", "")
                        if user_message:
                            utils.config.debug_print(f"[{self.name}] User message from webpage: {user_message}")
                            self._output_queues['user_text'].put(user_message)
                        return
                    
                    # Check for inactivity trigger - treat as user message to trigger generation
                    if data.get("inactivityTrigger"):
                        inactivity_message = data.get("message", "")
                        if inactivity_message:
                            utils.config.debug_print(f"[{self.name}] Inactivity detected, sending as user message to trigger generation")
                            # Route to user_text output so it triggers generation
                            self._output_queues['user_text'].put(inactivity_message)
                        return
                    
                    if message_type == "system_prompt":
                        # Send system message to LLM
                        cmd_id = str(uuid.uuid4())
                        cmd = {
                            "id": cmd_id,
                            "from": self.name,
                            "op": "APPEND",
                            "payload": {
                                "messages": [{
                                    "role": "system",
                                    "content": content
                                }]
                            }
                        }
                        utils.config.debug_print(f"[{self.name}] Sending system prompt: {content}")
                        self._output_queues['system_cmd'].put(cmd)
                        
                    elif message_type == "assistant_speech":
                        # Send assistant message to LLM for context
                        cmd_id = str(uuid.uuid4())
                        cmd = {
                            "id": cmd_id,
                            "from": self.name,
                            "op": "APPEND",
                            "payload": {
                                "messages": [{
                                    "role": "assistant",
                                    "content": content
                                }]
                            }
                        }
                        utils.config.debug_print(f"[{self.name}] Sending assistant message: {content}")
                        self._output_queues['assistant_cmd'].put(cmd)
                        
                        # Also send to TTS for speaking
                        utils.config.debug_print(f"[{self.name}] Sending to TTS: {content}")
                        self._output_queues['speech_text'].put(content)
                        
                    else:
                        # Unknown type or missing type - treat as regular operator command
                        utils.config.debug_print(f"[{self.name}] Unknown/missing type, treating as dict - passing through as string")
                        # Convert dict to string for passthrough
                        self._output_queues['passthrough_text'].put(str(data))
                else:
                    utils.config.debug_print(f"[{self.name}] Unknown data type: {type(data)}")

middle_modules_class['woz_handler'] = WoZHandler
