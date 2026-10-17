"""Independent signed-priority scan and explicit guest-memory fixtures."""
import itertools

from tools.experiments import game_record_maximum_scan as source
from tools.tests import game_viewport_initialize_oracle as machine

put, read, signed, STACK = machine.put, machine.read, machine.signed, machine.STACK
OUTPUT, COUNT, PRIMARY, ENABLED = 0x800C3640, 0x800C363A, 0x800C35D8, 0x800C35C8
PREFERRED, COUNTS, FALLBACK = 0x800C3688, 0x800C35D0, 0x800C3778
VALUES = (-32768, -9999, -1, 0, 1, 37, 32767)


def half(v): return ((v & 65535) ^ 32768) - 32768


def reference(initial, slot):
    m = dict(initial); out = OUTPUT + slot * 4; put(m, out, 0)
    count = read(m, COUNT + slot, 1)
    if not count: return m
    primary = read(m, PRIMARY + slot * 4)
    if read(m, primary, 2) >= 4:
        record = read(m, PREFERRED + slot * 120)
        override = half(read(m, record + 18, 2))
        if override != -9999:
            put(m, out, override & 0xFFFFFFFF); return m
    enabled = read(m, ENABLED + slot * 4); updated = False
    for index in range(count):
        if read(m, enabled + index * 2, 2) and read(m, primary + index * 2, 2):
            record = read(m, PREFERRED + slot * 120 + index * 4)
            current = signed(read(m, out)); value = half(read(m, record + 10, 2))
            if current < value: put(m, out, value & 0xFFFFFFFF); updated = True
    if updated: return m
    enabled = read(m, ENABLED + slot * 4)
    for index in range(count):
        if read(m, enabled + index * 2, 2):
            counts = read(m, COUNTS + slot * 4); entries = read(m, counts + index * 2, 2)
            if entries:
                record = read(m, FALLBACK + slot * 120 + index * 4)
                current = signed(read(m, out)); value = half(read(m, record + entries * 8 - 2, 2))
                if current < value: put(m, out, value & 0xFFFFFFFF)
    return m


def records(count, mode, seed):
    result = []
    for i in range(count):
        active = (0, 1, 0x100, 0x8000, 0xFFFF)[(seed + 3 * i) % 5]
        primary = (0, 1, 3)[(seed + i) % 3]
        entries = (0, 1, 2, 8)[(seed + i) % 4]
        value, tail = VALUES[(seed + i * 5) % 7], VALUES[(seed * 3 + i * 2 + 2) % 7]
        if mode == 1: active, primary, value, entries, tail = 1, 1, 7 + i, 1, 32767
        elif mode == 2: active, primary, value, entries, tail = 1, 1, -1 - i, 1, 17 + i
        elif mode == 5: active, primary, value, entries, tail = 0x100 << (i % 2), 1, -1, 2, 99 + i
        elif mode == 6: active = 0
        elif mode == 7: active, primary, value, entries, tail = 65535, 0, -1, (32768, 65535)[seed & 1], 32767
        elif mode == 8: active, primary, value, entries, tail = 1, 1, -1, 1, (17 if i == 0 else -1)
        if i == 0 and mode in (3, 4): primary = 4
        result.append((active, primary, value, entries, tail))
    return result


def cases():
    for slot, count, mode, seed in itertools.product(range(3), (0, 1, 2, 7, 30), range(4), (0, 3, 6)):
        yield slot, count, mode, seed, -9999
    for slot, override in itertools.product(range(3), VALUES): yield slot, 1, 4, 0, override
    for slot, mode, seed in itertools.product(range(3), (5, 7), (0, 1)): yield slot, (2 if mode == 5 else 1), mode, seed, -9999
    for count in (128, 255): yield 0, count, 6, 0, -9999
    for slot in range(3): yield slot, 2, 8, 0, -9999


def fixture(case):
    slot, count, mode, seed, override = case
    m = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-64, 256)}
    m.update({OUTPUT - 16 + i:0xA5 for i in range(44)})
    put(m, COUNT + slot, count, 1)
    enabled, primary, counts = 0x200000, 0x210000, 0x220000
    for at, value in ((ENABLED, enabled), (PRIMARY, primary), (COUNTS, counts)): put(m, at + slot * 4, value)
    for i, (active, present, value, entries, tail) in enumerate(records(count, mode, seed)):
        put(m, enabled + i * 2, active, 2); put(m, primary + i * 2, present, 2); put(m, counts + i * 2, entries, 2)
        if i >= 30: continue  # High-byte loop cases have no active record dereferences.
        record, fallback = 0x300000 + i * 32, 0x1000000 + i * 0x100000
        m.update({record + n:0xA5 for n in range(32)})
        m.update({fallback + n:0xA5 for n in range(80)})
        put(m, record + 10, value & 65535, 2); put(m, record + 18, override & 65535, 2)
        if entries: put(m, fallback + entries * 8 - 2, tail & 65535, 2)
        put(m, PREFERRED + slot * 120 + i * 4, record); put(m, FALLBACK + slot * 120 + i * 4, fallback)
    return m


def alias_cases():
    case = (1, 2, 2, 1, -9999); slot = case[0]
    for kind in ('primary', 'enabled', 'tail-count', 'preferred', 'tail'):
        m = fixture(case); out = OUTPUT + slot * 4
        if kind == 'primary': put(m, PRIMARY + slot * 4, out)
        elif kind == 'enabled': put(m, ENABLED + slot * 4, out)
        elif kind == 'tail-count': put(m, COUNTS + slot * 4, out)
        elif kind == 'preferred':
            put(m, PREFERRED + slot * 120, out - 10)
        elif kind == 'tail': put(m, FALLBACK + slot * 120, out - 6)
        yield kind, m, slot
    # A slot whose output word contains COUNT[slot] makes the clear visible there.
    slot = -2; m = fixture((0, 0, 0, 0, -9999)); put(m, OUTPUT + slot * 4, 0xFFFFFFFF)
    m[COUNT + slot] = 255
    yield 'clear-before-count', m, slot


class MaximumOracle(machine.InitializeOracle):
    def __init__(self, words, memory, slot, phase=0, helpers=None, entry=source.ENTRY):
        super().__init__(words, memory, (slot & 0xFFFFFFFF, 0x12345678, 0xFEDCBA98, 0x80000000),
            helpers or {}, phase, entry=entry)

    def record_call(self, target):
        if target != source.ENTRY: raise ValueError('Unexpected record maximum call: %X' % target)
        self.calls.append((target, self.arguments(1)))

    def hook(self, target): raise ValueError('Unexpected record maximum provider: %X' % target)


def state(m):
    return (m.memory, m.r, m.f, m.lo, m.events, m.calls, m.current_pc, m.delay_of, m.all_accesses)
