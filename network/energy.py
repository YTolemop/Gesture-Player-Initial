"""External ESP32 "energy can": a skill must be granted by it before release.

Serial line protocol (ASCII, newline terminated; see docs/esp32_energy.md):
    PING               -> PONG <energy> <capacity>
    REQ <id> <LABEL>   -> OK <id> <energy>  |  NO <id> <energy>
    REFUND <id>        -> REFUNDED <id> <energy>  |  NO <id> <energy>
Unrelated lines (boot log, late replies to timed-out requests) are ignored.
"""
import threading
import time

from network.commands import Commands

DEFAULT_GATED = ("ATTACK_SKILL", "DEFENSE_SKILL", "CONTROL_SKILL", "ULTIMATE")


class EnergyLink:
    """Request/reply transport to the ESP32. Use from one thread only."""

    def __init__(self, url, baudrate=115200, timeout=.15, boot_wait=3.0, port=None):
        if port is None:
            import serial
            # serial_for_url also accepts socket://host:port for a Wi-Fi bridge.
            port = serial.serial_for_url(url, baudrate=baudrate, timeout=.01)
        self.port = port
        self.timeout = timeout
        self.buffer = b""
        self.next_id = 1
        self.energy = None
        self.capacity = None
        try:
            self._handshake(boot_wait)
        except Exception:
            self.close()
            raise

    def _handshake(self, boot_wait):
        # Many ESP32 boards reboot when the port opens; retry PING until boot ends.
        deadline = time.monotonic() + boot_wait
        while time.monotonic() < deadline:
            self._write("PING")
            try:
                parts = self._wait(lambda p: p[0] == "PONG" and len(p) >= 3, .25)
            except TimeoutError:
                continue
            self.energy, self.capacity = int(parts[1]), int(parts[2])
            return
        raise RuntimeError("ESP32 energy can did not answer PING")

    def _write(self, line):
        self.port.write((line + "\n").encode("ascii"))

    def _lines(self):
        self.buffer += self.port.read(max(1, self.port.in_waiting))
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            parts = line.decode("ascii", "replace").split()
            if parts:
                yield parts

    def _wait(self, match, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            for parts in self._lines():
                try:
                    if match(parts):
                        return parts
                except (IndexError, ValueError):
                    continue
        raise TimeoutError("ESP32 energy can timed out")

    def _reply(self, kinds, ticket):
        parts = self._wait(lambda p: p[0] in kinds and int(p[1]) == ticket and len(p) >= 3)
        self.energy = int(parts[2])
        return parts[0]

    def request(self, label):
        """Return (granted, ticket). Raises TimeoutError if the ESP32 is silent."""
        ticket = self.next_id
        self.next_id += 1
        self._write(f"REQ {ticket} {label}")
        return self._reply(("OK", "NO"), ticket) == "OK", ticket

    def refund(self, ticket):
        self._write(f"REFUND {ticket}")
        return self._reply(("REFUNDED", "NO"), ticket) == "REFUNDED"

    def close(self):
        try:
            self.port.close()
        except Exception:
            pass


class EnergyGate:
    """Mask skill labels the energy can did not grant.

    The ESP32 is asked once per press. A press ends only after the label has
    been absent for `release` seconds, mirroring the arena's 6-tick re-arm, so
    recognition flicker neither re-asks nor wastes energy. Granted energy is
    refunded when the arena rejects the cast or never attempts it.
    """

    def __init__(self, link, gated=DEFAULT_GATED, release=.12, result_timeout=1.5,
                 fail_open=False, clock=time.monotonic, log=print):
        self.link = link
        self.gated = frozenset(gated)
        self.release = release
        self.result_timeout = result_timeout
        self.fail_open = fail_open
        self.clock = clock
        self.log = log
        self.lock = threading.Lock()
        self.decisions = {}      # label -> granted for the current press
        self.absent_since = {}   # label -> time it disappeared
        self.tickets = {}        # label -> [(ticket or None, deadline)] awaiting input:result
        self.refunds = []        # tickets to refund, filled from the Socket.IO thread
        self.last_error = float("-inf")

    def reset(self):
        """Arena context changed: forget presses; pending tickets still resolve."""
        self.decisions.clear()
        self.absent_since.clear()

    def on_result(self, event):
        """Socket.IO `input:result` handler; serial I/O is deferred to filter()."""
        label = event.get("label") if isinstance(event, dict) else None
        with self.lock:
            queue = self.tickets.get(label)
            if not queue:
                return
            ticket, _ = queue.pop(0)
            if ticket is not None and event.get("reason") != "OK":
                self.refunds.append(ticket)

    def filter(self, commands: Commands) -> Commands:
        now = self.clock()
        present = [v for v in (commands.left, commands.right, commands.both) if v in self.gated]
        for label in list(self.decisions):
            if label in present:
                self.absent_since.pop(label, None)
            elif now - self.absent_since.setdefault(label, now) >= self.release:
                del self.decisions[label]
                del self.absent_since[label]
        for label in present:
            if label not in self.decisions:
                self.decisions[label] = self._ask(label, now)
        self._settle(now)

        def mask(value):
            return "NONE" if value in self.gated and not self.decisions.get(value) else value
        return Commands(mask(commands.left), mask(commands.right), mask(commands.both))

    def _ask(self, label, now):
        try:
            granted, ticket = self.link.request(label)
        except Exception as exc:
            if now - self.last_error >= 2:
                self.log(f"Energy can error: {exc}; {'allowing' if self.fail_open else 'blocking'} skills")
                self.last_error = now
            granted, ticket = self.fail_open, None
        else:
            self.log(f"Energy {'granted' if granted else 'denied'}: {label} (energy={self.link.energy})")
        if granted:
            with self.lock:
                self.tickets.setdefault(label, []).append((ticket, now + self.result_timeout))
        return granted

    def _settle(self, now):
        with self.lock:
            for queue in self.tickets.values():
                while queue and queue[0][1] <= now:
                    ticket, _ = queue.pop(0)
                    if ticket is not None:
                        self.refunds.append(ticket)
            refunds, self.refunds = self.refunds, []
        for ticket in refunds:
            try:
                self.link.refund(ticket)
            except Exception as exc:
                self.log(f"Energy refund {ticket} failed: {exc}")
