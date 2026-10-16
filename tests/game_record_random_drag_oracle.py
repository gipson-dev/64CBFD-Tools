"""Record callback 6: independent public effects and bounded literal guest probes."""
from tools.experiments import game_record_random_drag as source
from tools.tests import test_game_record_fade_callback as fade
from tools.tests.test_game_random_reload_timer_match import TimerOracle

STACK, RECORD, OTHER = fade.STACK, fade.RECORD, fade.OTHER
put, read, signed, short, external = fade.put, fade.read, fade.signed, fade.short, fade.external
AccessFault = fade.AccessFault


def fixture(value=128, active=1, delta=1, velocity=32, flags=0, phase=0, record=RECORD):
    memory = fade.fixture(value, active, delta, record=record, phase=phase)
    for offset, data, width in ((0x23, 6, 1), (0x26, velocity >> 8, 1), (0x27, velocity, 1),
            (0x28, 0x80, 1), (0x29, 0xA5, 1), (0x2F, flags, 1)):
        put(memory, record + offset, data, width)
    return memory


def effects(target, ordinal, record, mode):
    if mode == 1 and target == source.LIFETIME_RANDOM:
        return ((record + 0x1F, 231, 1), (source.STEP, 2, 4))
    if mode == 2 and target == source.MOVE:
        return ((record + 0x2F, 0, 1), (record + 0x26, 0, 1),
            (record + 0x27, 32, 1), (source.STEP, 0x87654321, 4))
    if mode == 3 and target == source.SCALE_X:
        return ((record + 0x2F, 0, 1), (record + 0x26, 0, 1), (record + 0x27, 0, 1))
    return ()


def remainder32(word):
    value = signed(word)
    return value % 32 if value >= 0 else -((-value) % 32)


def reference(memory, randoms=(0xFFFFFFFF, 0x80000001), lifetime=0xFFFFFFFF,
        mode=0, record=RECORD, step=source.STEP, move=source.MOVE,
        scale_x=source.SCALE_X, scale_z=source.SCALE_Z,
        random=source.RANDOM, lifetime_random=source.LIFETIME_RANDOM):
    memory, calls = dict(memory), []
    value, active = read(memory, record + 0x1F, 1), read(memory, record + 0x24, 1)

    def call(target, *args):
        calls.append((target, *args))
        role = {move: source.MOVE, scale_x: source.SCALE_X, scale_z: source.SCALE_Z,
            lifetime_random: source.LIFETIME_RANDOM, random: source.RANDOM}[target]
        for at, data, size in effects(role, len(calls), record, mode):
            put(memory, at, data, size)

    def store():
        put(memory, record + 0x1F, value, 1)
        if mode == 4:
            put(memory, record + 0x24, not read(memory, record + 0x24, 1), 1)

    if active:
        if value == 0:
            call(lifetime_random)
            put(memory, record + 0x24, (lifetime & 0xFFFFFFFF) % 25 + 200, 1)
        if value != 254:
            value = signed(value + (read(memory, step) << 6))
            if value >= 255:
                value = 254
            store()
    elif value:
        value = max(0, signed(value - (read(memory, step) << 4)))
        store()
    if read(memory, record + 0x24, 1) == 0 and value == 0:
        return external(memory), calls, 1
    call(move, record)
    flags = read(memory, record + 0x2F, 1)
    velocity = 0
    if not flags:
        velocity = (read(memory, record + 0x26, 1) - (256 if read(memory, record + 0x26, 1) & 128 else 0)) * 256
        velocity += read(memory, record + 0x27, 1)
    if flags or signed(velocity * velocity * 2) >= 2001:
        base = 230 if flags else 220
        call(random)
        call(scale_x, record, remainder32(randoms[0]) + base)
        call(random)
        call(scale_z, record, remainder32(randoms[1]) + base)
    put(memory, record + 0x18, 0, 2)
    return external(memory), calls, 0


class DragOracle(fade.FadeOracle):
    def __init__(self, words, memory, randoms=(0xFFFFFFFF, 0x80000001), lifetime=0xFFFFFFFF,
            phase=0, mode=0, fault=None, record=RECORD, entry=source.ENTRY,
            step=source.STEP, move=source.MOVE, scale_x=source.SCALE_X,
            scale_z=source.SCALE_Z, random=source.RANDOM, lifetime_random=source.LIFETIME_RANDOM,
            connected=None):
        super().__init__(words, memory, phase=phase, mode=0, fault=fault, record=record,
            entry=entry, step=step, move=move, connected=connected)
        self.mode, self.flip_store, self.randoms, self.lifetime = mode, False, randoms, lifetime
        self.scale_x, self.scale_z = scale_x, scale_z
        self.random, self.lifetime_random, self.random_count = random, lifetime_random, 0
        self.hi = self.lo = 0

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 25:
            self.dispatched_word = word
            product = self.r[word >> 21 & 31] * self.r[word >> 16 & 31]
            self.hi, self.lo = product >> 32 & 0xFFFFFFFF, product & 0xFFFFFFFF
        elif word >> 26 == 0 and word & 63 in (27, 16):
            self.dispatched_word, self.own_instruction = word, True
            try:
                TimerOracle.execute(self, word)
            finally:
                self.own_instruction = False
        else:
            super().execute(word)

    def put(self, address, value, width):
        super().put(address, value, width)
        if self.mode == 4 and self.own_instruction and address == self.record + 0x1F and width == 1:
            self.own_instruction = False
            try:
                super().put(self.record + 0x24, not self.peek(self.record + 0x24, 1), 1)
            finally:
                self.own_instruction = True

    def record_call(self, target):
        count = {self.lifetime_random: 0, self.random: 0, self.move: 1,
            self.scale_x: 2, self.scale_z: 2, source.ENTRY: 1, 0x1516972C: 1}[target]
        args = self.arguments(count)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        value = self.lifetime if target == self.lifetime_random else 0xABCDEF01
        if target == self.random:
            value = self.randoms[self.random_count % 2]
            self.random_count += 1
        role = {self.move: source.MOVE, self.scale_x: source.SCALE_X, self.scale_z: source.SCALE_Z,
            self.random: source.RANDOM, self.lifetime_random: source.LIFETIME_RANDOM,
            0x1516972C: 0x1516972C}[target]
        for at, data, size in effects(role, len(self.calls), self.record, self.mode):
            self.put(at, data, size)
        if self.mode == 5 and target == self.move:
            self.put(STACK + self.phase, OTHER, 4)
        if target == 0x1516972C:
            self.put(self.record + 0x2E, 0x6D, 1)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (*range(1, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo, self.condition = 0x87654321, 0x12345678, True
        self.r[2] = value & 0xFFFFFFFF


def state(model):
    return (model.memory, model.r, model.f, model.hi, model.lo, model.condition,
        model.events, model.calls, model.accesses)
