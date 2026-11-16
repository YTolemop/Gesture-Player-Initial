import pytest
from network.commands import Commands
from network.energy import EnergyGate, EnergyLink

COSTS = {"ATTACK_SKILL": 1, "DEFENSE_SKILL": 1, "CONTROL_SKILL": 2, "ULTIMATE": 3}


class FakeCan:
    """Serial port double that follows the firmware protocol."""

    def __init__(self, energy=3, capacity=6, chunk=4096, boot=b""):
        self.energy = energy
        self.capacity = capacity
        self.chunk = chunk
        self.output = boot
        self.silent = False
        self.writes = []
        self.tickets = {}

    @property
    def in_waiting(self):
        return len(self.output)

    def read(self, size):
        data, self.output = self.output[:min(size, self.chunk)], self.output[min(size, self.chunk):]
        return data

    def write(self, data):
        text = data.decode("ascii").strip()
        self.writes.append(text)
        if self.silent:
            return
        parts = text.split()
        if parts[0] == "PING":
            self.output += f"PONG {self.energy} {self.capacity}\n".encode()
        elif parts[0] == "REQ":
            ticket, cost = int(parts[1]), COSTS.get(parts[2], -1)
            if 0 <= cost <= self.energy:
                self.energy -= cost
                self.tickets[ticket] = cost
                kind = "OK"
            else:
                kind = "NO"
            self.output += f"{kind} {ticket} {self.energy}\n".encode()
        elif parts[0] == "REFUND":
            ticket = int(parts[1])
            cost = self.tickets.pop(ticket, None)
            if cost is not None:
                self.energy = min(self.capacity, self.energy + cost)
            kind = "NO" if cost is None else "REFUNDED"
            self.output += f"{kind} {ticket} {self.energy}\n".encode()

    def close(self):
        pass

    def requests(self):
        return [w for w in self.writes if w.startswith("REQ")]


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def gate(can, **kwargs):
    clock = Clock()
    link = EnergyLink("fake", port=can, timeout=.05, boot_wait=.5)
    return EnergyGate(link, clock=clock, log=lambda *_: None, **kwargs), clock


def test_handshake_skips_boot_noise_and_partial_lines():
    can = FakeCan(energy=4, chunk=3, boot=b"\x00rst:0x1 boot\nREADY 4 6\n")
    link = EnergyLink("fake", port=can, timeout=.05, boot_wait=.5)
    assert (link.energy, link.capacity) == (4, 6)


def test_silent_device_fails_to_connect():
    can = FakeCan()
    can.silent = True
    with pytest.raises(RuntimeError):
        EnergyLink("fake", port=can, timeout=.05, boot_wait=.3)


def test_grant_passes_skill_and_holding_asks_once():
    can = FakeCan(energy=3)
    g, clock = gate(can)
    for _ in range(5):
        assert g.filter(Commands("MOVE_LEFT", "ATTACK_SKILL")) == Commands("MOVE_LEFT", "ATTACK_SKILL")
        clock.now += .03
    assert len(can.requests()) == 1
    assert can.energy == 2


def test_denied_skill_becomes_none_but_other_channels_pass():
    can = FakeCan(energy=2)
    g, _ = gate(can)
    assert g.filter(Commands("BLOCK", "ULTIMATE")) == Commands("BLOCK", "NONE")
    assert g.filter(Commands(both="ULTIMATE")) == Commands()
    assert can.energy == 2
    assert len(can.requests()) == 1


def test_ungated_labels_never_ask():
    can = FakeCan()
    g, _ = gate(can)
    assert g.filter(Commands("JUMP", "NORMAL_ATTACK")) == Commands("JUMP", "NORMAL_ATTACK")
    assert can.requests() == []


def test_flicker_keeps_press_and_release_allows_next_press():
    can = FakeCan(energy=6)
    g, clock = gate(can)
    g.filter(Commands(right="ATTACK_SKILL"))
    clock.now += .05
    g.filter(Commands())
    clock.now += .05
    g.filter(Commands(right="ATTACK_SKILL"))
    assert len(can.requests()) == 1
    clock.now += .05
    g.filter(Commands())
    clock.now += .2
    g.filter(Commands())
    g.filter(Commands(right="ATTACK_SKILL"))
    assert len(can.requests()) == 2


def test_arena_rejection_refunds_and_success_keeps_energy():
    can = FakeCan(energy=6)
    g, clock = gate(can)
    g.filter(Commands(right="CONTROL_SKILL"))
    assert can.energy == 4
    g.on_result({"type": "input", "label": "CONTROL_SKILL", "reason": "COOLDOWN"})
    g.filter(Commands(right="CONTROL_SKILL"))
    assert can.energy == 6
    g.filter(Commands())
    clock.now += .2
    g.filter(Commands())
    g.filter(Commands(right="CONTROL_SKILL"))
    g.on_result({"type": "input", "label": "CONTROL_SKILL", "reason": "OK"})
    clock.now += 5
    g.filter(Commands())
    assert can.energy == 4


def test_unattempted_grant_is_refunded_after_timeout():
    can = FakeCan(energy=6)
    g, clock = gate(can)
    g.filter(Commands(both="ULTIMATE"))
    assert can.energy == 3
    clock.now += 1.6
    g.filter(Commands())
    assert can.energy == 6


def test_silent_device_blocks_by_default_or_allows_when_fail_open():
    for fail_open, expected in ((False, Commands()), (True, Commands(right="ATTACK_SKILL"))):
        can = FakeCan()
        g, _ = gate(can, fail_open=fail_open)
        can.silent = True
        assert g.filter(Commands(right="ATTACK_SKILL")) == expected


def test_reset_forgets_held_press():
    can = FakeCan(energy=6)
    g, _ = gate(can)
    g.filter(Commands(right="ATTACK_SKILL"))
    g.reset()
    g.filter(Commands(right="ATTACK_SKILL"))
    assert len(can.requests()) == 2
