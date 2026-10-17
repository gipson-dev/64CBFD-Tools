"""Ordered reset/reference and bounded opaque versus actual helper contracts."""
import itertools

from tools.experiments import game_sequence_state_reset as source
from tools.tests import game_viewport_initialize_oracle as machine

put, read, signed, STACK = machine.put, machine.read, machine.signed, machine.STACK
LIMIT, HELPER, ZERO, TABLE = 0x800969C0, 0x150233BC, 0x100226F0, 0x800C3CA0
MASK = 0xFFFFFFFF
# Address, width, value, indexed. None is the shared float limit captured at entry.
STORES = (
    (0x800C35B8,4,-100,True), (0x800C35B0,4,0,True), (0x800C35C0,1,0,True),
    (0x800C3C8E,2,0,False), (0x800C363A,1,0,True), (0x800C35EA,1,0,True),
    (0x800C3D50,4,0,False), (0x800C35F8,1,255,False),
    (0x800C3648,4,0,False), (0x800C364C,4,0,False), (0x800C3650,4,0,False),
    (0x800C3654,1,0,True), (0x800C3656,1,0,True), (0x800C3658,1,1,True),
    (0x800C365A,1,0,True), (0x800C365C,1,0,True), (0x800C365E,1,0,True), (0x800C3660,1,0,True),
    (0x800C3638,1,0,False), (0x800C3662,1,0,False), (0x800C3C8C,1,0,False),
    (0x800C3C8D,1,0,False), (0x800C35C2,1,0,False), (0x800C3A58,1,0,False),
    (0x800C35A4,4,0,False), (0x800C3C8A,1,-1,False), (0x800C3C8B,1,0,False),
    (0x800C3674,4,None,False), (0x800C3678,4,None,False), (0x800C367C,4,0,False),
    (0x800C3680,1,0,False), (0x800C3672,1,0,False), (0x800C3C9D,1,100,False), (0x800C3C9E,2,-1,False))
LIMITS = (0x4479C000, 0, 0x80000000, 0xC479C000, 0x7F800000, 0x7FC12345, 0x3F000000, 0x7F7FFFFF)


def public(memory): return {a:v for a,v in memory.items() if not STACK - 0x200 <= a < STACK + 0x100}


def effects(memory, slot, mode):
    fired = []
    if mode & 1:
        put(memory, (0x800C35B8 + slot * 4) & MASK, 1234)
        put(memory, 0x800C3674, 0xBF800000); fired.append(1)
    if mode & 2:
        put(memory, 0x8008FD84, 127, 1); put(memory, 0x800C3670, 128, 1)
        put(memory, 0x800C3C9E, 0x1234, 2); fired.append(2)
    if mode & 4:
        put(memory, LIMIT, 0x3FC00000); put(memory, 0x800C3D50, 0x80405678); fired.append(4)
    if mode & 8:
        put(memory, (0x800C363A + slot) & MASK, 254, 1)
        put(memory, TABLE + 167, 0x77, 1); fired.append(8)
    return fired


def reference(initial, slot, mode=0):
    memory = dict(initial); limit = read(memory, LIMIT)
    for base, width, value, indexed in STORES:
        address = (base + (slot * width if indexed else 0)) & MASK
        put(memory, address, (limit if value is None else value) & ((1 << (width * 8)) - 1), width)
    before = public(memory)
    for i in range(168): memory[TABLE + i] = 0
    fired = effects(memory, slot, mode)
    put(memory, 0x8008FD84, 0, 1); put(memory, 0x800C3670, 0, 1)
    return memory, before, fired


def fixture(slot=0, limit=0x4479C000, pattern=1):
    memory = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-0x200, 0x100)}
    for base, size in ((0x800C3500, 0x860), (LIMIT - 8, 20), (0x8008FD80, 16)):
        memory.update({base + i:(i * (13 if pattern == 1 else 0) + (0 if pattern == 0 else 0xFF if pattern == 255 else 0xA5)) & 255 for i in range(size)})
    for base, width, _, indexed in STORES:
        address = (base + (slot * width if indexed else 0)) & MASK
        for i in range(-8, width + 8): memory.setdefault((address + i) & MASK, (i * 17 + 0xA5) & 255)
    put(memory, LIMIT, limit)
    return memory


def cases(native=False):
    for slot, limit, pattern, mode in itertools.product((0, 1), LIMITS, (0, 1, 255), (0, 1, 2, 4, 8, 15)):
        yield slot, limit, pattern, mode
    if not native:
        for slot, limit, mode in itertools.product((-1, 2, 3, 0x40000000, -0x80000000, 0x7FFFFFFF, -45822, -45820),
                (0x4479C000, 0x80000000), (0, 15)):
            yield slot, limit, 1, mode


class ResetOracle(machine.InitializeOracle):
    def __init__(self, words, memory, slot, phase=0, mode=0, helpers=None, entry=source.ENTRY, arguments=None):
        super().__init__(words, memory, (slot & MASK, 0x12345678, 0xFEDCBA98, 0x80000000) if arguments is None else arguments,
            helpers or {}, phase, entry=entry)
        self.slot, self.provider_mode = signed(slot), mode
        self.observations, self.fired = [], []

    def record_call(self, target):
        if target == source.ENTRY:
            self.slot = signed(self.r[4]); packet = (self.r[4],)
        elif target == HELPER:
            packet = (); self.observations.append(public(self.memory))
        elif target == ZERO: packet = self.arguments(2)
        else: raise ValueError('Unexpected sequence-reset provider: %X' % target)
        self.calls.append((target, packet)); self.events.append(('CALL', target, packet))

    def hook(self, target):
        if target not in (HELPER, ZERO): raise ValueError('Unexpected sequence-reset hook')
        if target == ZERO and self.arguments(2) != (TABLE, 168): raise ValueError('Unknown actor-table clear packet')
        for i in range(168): self.put(TABLE + i, 0, 1)
        # Diagnostic mutation belongs to the opaque helper contract, not retail bzero.
        if target == HELPER: self.fired.extend(effects(self.memory, self.slot, self.provider_mode))
        elif self.provider_mode: raise ValueError('Diagnostic mutations are not a retail bzero contract')
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344


def state(m):
    return (m.memory, m.r, m.f, m.lo, m.events, m.calls, m.observations, m.fired, m.current_pc, m.delay_of, m.all_accesses)
