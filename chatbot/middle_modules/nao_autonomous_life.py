# chatbot/middle_modules/nao_autonomous_life.py
import qi
import time
import utils.nao
import utils.config
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot


class _LifeCallback(qi.Object):
    """Registered qi service that receives ALMemory event notifications.

    ALMemory.subscribeToEvent() can only deliver to a *named* module method
    (the on-robot C++ callback model), so the callback must be a qi.Object
    registered on the session. The handler thread it runs on is a qi
    event-loop thread, not the module's own thread, so the handler only
    records the event name into a thread-safe set; the module's action()
    loop polls that set and does all queue I/O on its own thread.
    """

    def __init__(self, events_seen):
        super().__init__()
        self._events_seen = events_seen  # set, GIL-protected

    def onEvent(self, data):
        self._events_seen.add(data)


class NaoAutonomousLife(DummyMiddle):
    """Drives the NAO's ALAutonomousLife service and mirrors its state.

    Queues:
        input slots:
            state: string
                "solitary" | "interactive" | "disabled"
                Triggers setState() on the NAO.
            focus: string
                An activity name to switchFocus() to.
        output slots:
            default: string
                Emits the current life state ("solitary", "interactive",
                "disabled", "safeguard") whenever it changes, and once on
                startup after the boot state has been applied.
            focused: string
                Emits the currently focused activity name (possibly empty
                string) whenever it changes.

    Args:
        ip: NAO IP address (default 127.0.0.1)
        port: NAOqi port (default 9559)
        boot_state: state to apply on module_start (default "solitary")
        set_state_retries: how many times to retry setState on startup
            (default 10); the NAO's boot-config behavior leaves
            AutonomousLife in a window where setState is refused, so a
            bounded retry is needed.
        set_state_retry_wait: seconds between setState retries (default 0.5)
        poll_interval: seconds between action() polls when idle
            (default 0.05)
    """

    _VALID_STATES = ("solitary", "interactive", "disabled")

    def __init__(self, name="nao_autonomous_life", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "string"
        self.datatype_out = "string"

        # Extra input slots
        self._input_queues["state"] = QueueSlot(self, "input", datatype="string")
        self._input_queues["focus"] = QueueSlot(self, "input", datatype="string")
        # Extra output slot
        self._output_queues["focused"] = QueueSlot(self, "output", datatype="string")

        self.ip = args.get("ip", "127.0.0.1")
        self.port = args.get("port", 9559)
        self.boot_state = args.get("boot_state", "solitary")
        self.set_state_retries = args.get("set_state_retries", 10)
        self.set_state_retry_wait = args.get("set_state_retry_wait", 0.5)
        self.poll_interval = args.get("poll_interval", 0.05)

        self.session = None
        self.life = None
        self.memory = None
        self._callback = None
        self._callback_name = f"NaoAutonomousLifeCallback_{self.name}"
        self._events_seen = set()
        self._last_state = None
        self._last_focus = None

    def _connect(self):
        self.session = utils.nao.connect(self.ip, self.port)
        self.life = self.session.service("ALAutonomousLife")
        self.memory = self.session.service("ALMemory")

        # Register the event callback as a named qi service so
        # ALMemory.subscribeToEvent() can deliver to it.
        self._callback = _LifeCallback(self._events_seen)
        self.session.registerService(self._callback_name, self._callback)
        self.memory.subscribeToEvent(
            "AutonomousLife/State", self._callback_name, "onEvent")
        self.memory.subscribeToEvent(
            "AutonomousLife/FocusedActivity", self._callback_name, "onEvent")

        utils.config.debug_print(
            f"[{self.name}] Connected to NAO at {self.ip}:{self.port}, "
            f"subscribed to AutonomousLife events")

    def _disconnect(self):
        try:
            if self.memory is not None and self._callback is not None:
                self.memory.unsubscribeToEvent(
                    "AutonomousLife/State", self._callback_name)
                self.memory.unsubscribeToEvent(
                    "AutonomousLife/FocusedActivity", self._callback_name)
        except Exception as e:
            utils.config.debug_print(f"[{self.name}] Error unsubscribing: {e}")
        try:
            if self.session is not None and self._callback is not None:
                self.session.unregisterService(self._callback_name)
        except Exception as e:
            utils.config.debug_print(f"[{self.name}] Error unregistering callback: {e}")
        try:
            utils.nao.disconnect(self.ip, self.port)
        except Exception as e:
            utils.config.debug_print(f"[{self.name}] Error disconnecting: {e}")
        utils.config.debug_print(f"[{self.name}] Disconnected from NAO")

    def _set_state_with_retry(self, state):
        """Call setState(), retrying on the boot-window refusal.

        During early boot the NAO's boot-config behavior leaves
        ALAutonomousLife in a state where setState() is refused with
        "Calls to the setState method are not currently allowed." A
        bounded retry over a few seconds gets through once the
        Launchpad machinery is up.
        """
        for attempt in range(self.set_state_retries):
            try:
                self.life.setState(state)
                utils.config.debug_print(
                    f"[{self.name}] setState({state!r}) succeeded "
                    f"(attempt {attempt + 1})")
                return True
            except Exception as e:
                utils.config.debug_print(
                    f"[{self.name}] setState({state!r}) refused "
                    f"(attempt {attempt + 1}/{self.set_state_retries}): {e}")
                if attempt < self.set_state_retries - 1:
                    time.sleep(self.set_state_retry_wait)
        utils.config.debug_print(
            f"[{self.name}] setState({state!r}) failed after "
            f"{self.set_state_retries} attempts")
        return False

    def module_start(self):
        self._connect()
        if self.boot_state:
            self._set_state_with_retry(self.boot_state)
        # Emit the initial state so downstream consumers know the robot is up.
        try:
            self._last_state = self.life.getState()
        except Exception as e:
            utils.config.debug_print(f"[{self.name}] Initial getState failed: {e}")
            self._last_state = None
        utils.config.debug_print(
            f"[{self.name}] Started, boot_state={self.boot_state!r}, "
            f"actual state={self._last_state!r}")

    def module_stop(self):
        utils.config.debug_print(f"[{self.name}] Stopping")
        self._disconnect()

    def action(self, i):
        # 1. Handle an explicit state request
        state_req = self._input_queues["state"].get()
        if state_req is not None:
            if state_req not in self._VALID_STATES:
                utils.config.debug_print(
                    f"[{self.name}] Ignoring invalid state {state_req!r}, "
                    f"expected one of {self._VALID_STATES}")
            else:
                self._set_state_with_retry(state_req)

        # 2. Handle an explicit focus request
        focus_req = self._input_queues["focus"].get()
        if focus_req is not None:
            try:
                self.life.switchFocus(focus_req)
                utils.config.debug_print(
                    f"[{self.name}] switchFocus({focus_req!r})")
            except Exception as e:
                utils.config.debug_print(
                    f"[{self.name}] switchFocus({focus_req!r}) failed: {e}")

        # 3. Poll for events seen by the callback thread
        if self._events_seen:
            events = list(self._events_seen)
            self._events_seen.clear()
            # Re-read state/focus now that an event fired
            new_state = None
            new_focus = None
            try:
                new_state = self.life.getState()
            except Exception:
                pass
            try:
                new_focus = self.life.focusedActivity()
            except Exception:
                pass
            if new_state is not None and new_state != self._last_state:
                utils.config.debug_print(
                    f"[{self.name}] State changed: {self._last_state!r} -> "
                    f"{new_state!r}")
                self._last_state = new_state
                self._safe_put_state(new_state)
            if new_focus is not None and new_focus != self._last_focus:
                utils.config.debug_print(
                    f"[{self.name}] Focus changed: {self._last_focus!r} -> "
                    f"{new_focus!r}")
                self._last_focus = new_focus
                self._safe_put_focus(new_focus)
            return  # processed, don't sleep

        # 4. Emit initial state once (after boot_state applied in module_start)
        if self._last_state is not None:
            # Only emit the initial state if we haven't emitted anything yet.
            # Use a sentinel: _last_focus is None until first read.
            if self._last_focus is None:
                self._safe_put_state(self._last_state)
                try:
                    self._last_focus = self.life.focusedActivity()
                except Exception:
                    self._last_focus = ""
                self._safe_put_focus(self._last_focus)
                return

        time.sleep(self.poll_interval)

    def _safe_put_state(self, state):
        """Emit state on the default output slot if any consumer is linked.

        QueueWrapper.put() raises ValueError when no downstream module is
        bound to the queue; guard against that so the module can run in
        isolation (e.g. tests) without a consumer.
        """
        try:
            self.output_queue.put(state)
        except ValueError:
            pass

    def _safe_put_focus(self, focus):
        """Emit focused activity on the focused output slot if any consumer
        is linked."""
        try:
            self._output_queues["focused"].put(focus)
        except ValueError:
            pass


middle_modules_class["nao_autonomous_life"] = NaoAutonomousLife
