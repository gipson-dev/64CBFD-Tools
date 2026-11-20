"""Independent bounded timer/callback contracts for the trail update."""
from dataclasses import dataclass
import itertools

from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read

ENTRY = 0x1510608C
RECORD, CHILD0, CHILD1, TABLE, TICKS = 0x30000, 0x40000, 0x50000, 0x80088C10, 0x800BE9E4
CALLBACKS = (0x15107924, 0x15107E48)
REMOVE, CURVE, SAMPLES, RNG = 0x1516972C, 0x15106214, 0x15106610, 0x150ADA20
COUNTS = {**{a: 2 for a in CALLBACKS}, REMOVE: 1, CURVE: 1, SAMPLES: 1, RNG: 0}
u32 = lambda n: n & 0xFFFFFFFF
half = lambda n: ((n & 65535) ^ 32768) - 32768
byte = lambda n: ((n & 255) ^ 128) - 128


@dataclass(frozen=True)
class Case:
    flag: int
    null: int
    returned: int
    changed: int
    seed: int
    mode: int
    phase: int


def cases():
    for row in itertools.product((-1, 0, 1), (0, 1), (0, 0x80000000),
                                 (0, 255), range(8), range(4), (0, 8)):
        yield Case(*row)


def fixture(c):
    m = {STACK+i: (i*17+c.seed*13+0xA5)&255 for i in range(-256, 256)}
    for base, length in ((RECORD-16, 0xA8), (CHILD0-16, 0x80), (CHILD1-16, 0x80)):
        m.update({base+i: (i*29+c.seed*11+0x5A)&255 for i in range(length)})
    for i, target in enumerate(CALLBACKS):
        put(m, TABLE+4*i, 0 if c.null else target)
    put(m, TICKS, (0, 1, 0xFFFFFFFF, 7, 32767, 65536, 0x80000000, 0x7FFFFFFF)[c.seed])
    m[RECORD+0x44] = c.flag & 255
    m[RECORD+0x12] = (0, 1, 2, 255)[c.seed % 4]
    put(m, RECORD+0x10, (0, 1, -1, 32767, -32768, 7, 0xFFFF, 2)[c.seed], 2)
    put(m, RECORD+0x68, (0, 1, -1, 32767, -32768, 7, 0xFFFF, 2)[7-c.seed], 2)
    put(m, RECORD+0x54, (-32768, -1, 0, 32767)[c.seed % 4], 2)
    put(m, RECORD+0x56, (0, 1, 32767, -32768)[c.seed % 4], 2)
    put(m, RECORD+0x6C, CHILD0 if c.seed & 1 else 0)
    put(m, RECORD+0x70, CHILD1 if c.seed & 2 else 0)
    # Copy all bit patterns without floating arithmetic, including NaNs.
    for i, offset in enumerate((0x14, 0x18, 0x1C, 0x38, 0x3C, 0x40)):
        put(m, RECORD+offset, (0x80000000, 0x7FC01234, 0x7F800001, 0, 0xFFFFFFFF, 0x3F800000)[(i+c.seed)%6])
    return m


def random_value(c):
    return (0, 1, 0xFFFFFFFF, 0x80000000, 7, 0x87654321, 32767, 0xFFFFFFFE)[c.seed]


def effect(m, c, target, changed):
    if target in CALLBACKS:
        m[changed] = c.changed
        if c.mode & 1:
            m[RECORD+0x12] ^= 1
            put(m, TICKS, 3)
            put(m, RECORD+0x10, 2, 2)
            put(m, RECORD+0x38, 0x7FC0ABCD)
    elif target == REMOVE and c.mode & 2:
        if changed is not None:
            m[changed] ^= 0x81
        put(m, TICKS, 0xFFFFFFFF)
        put(m, RECORD+0x68, -2, 2)
    elif target == CURVE and c.mode & 1:
        put(m, TICKS, 65537)
        put(m, RECORD+0x14, 0xDEADBEEF)
    elif target == SAMPLES and c.mode & 2:
        put(m, RECORD+0x54, 123, 2)
        put(m, RECORD+0x56, 7, 2)
    elif target == RNG and c.mode & 1:
        put(m, RECORD+0x54, -123, 2)
        put(m, RECORD+0x56, -32768, 2)
        put(m, RECORD+0x6C, CHILD1)


def public(m):
    return {a: b for a, b in m.items() if not STACK-256 <= a < STACK+256}


def reference(initial, c):
    m, calls, changed_ptr = dict(initial), [], None
    changed_home = STACK+c.phase-5
    m[changed_home] = 0
    def call(target, *args):
        nonlocal changed_ptr
        calls.append((target, tuple(map(u32, args))))
        if target in CALLBACKS:
            changed_ptr = args[1]
        effect(m, c, target, changed_ptr)
        return c.returned if target in CALLBACKS else random_value(c) if target == RNG else 0
    flag = byte(m[RECORD+0x44])
    if flag != -1:
        target = read(m, TABLE+flag*4)
        if target and call(target, RECORD, changed_home) == 0:
            call(REMOVE, RECORD)
    if m[RECORD+0x12] & 1:
        put(m, RECORD+0x10, half(read(m, RECORD+0x10, 2))-read(m, TICKS), 2)
        if half(read(m, RECORD+0x10, 2)) < 0:
            call(REMOVE, RECORD)
    if m[changed_home]:
        call(CURVE, RECORD)
    put(m, RECORD+0x68, half(read(m, RECORD+0x68, 2))-read(m, TICKS), 2)
    if half(read(m, RECORD+0x68, 2)) < 0:
        call(SAMPLES, RECORD)
        value = call(RNG)
        divisor = u32(half(read(m, RECORD+0x56, 2))+1)
        assert divisor
        put(m, RECORD+0x68, value % divisor + half(read(m, RECORD+0x54, 2)), 2)
    for index, offset in ((0, 0x14), (1, 0x38)):
        child = read(m, RECORD+0x6C+4*index)
        if child:
            for lane in range(3):
                put(m, child+0x40+4*lane, read(m, RECORD+offset+4*lane))
    return m, calls


class UpdateOracle(TimingOracle):
    def __init__(self, words, memory, c):
        self.case, self.changed_ptr = c, None
        super().__init__(words, memory, phase=c.phase, entry=ENTRY, arguments=(RECORD,))

    def execute(self, word):
        if word >> 26 == 32:  # Signed callback selector.
            rs, rt = word >> 21 & 31, word >> 16 & 31
            imm = half(word)
            self.r[rt] = u32(byte(self.get(u32(self.r[rs]+imm), 1)))
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in COUNTS, hex(target)
        args = tuple(map(u32, self.arguments(COUNTS[target])))
        self.calls.append((target, args))
        if target in CALLBACKS:
            assert args == (RECORD, STACK+self.case.phase-5)
            self.changed_ptr = args[1]

    def hook(self, target):
        effect(self.memory, self.case, target, self.changed_ptr)
        value = self.case.returned if target in CALLBACKS else random_value(self.case) if target == RNG else 0xDEADBEEF
        for i in range(4):
            put(self.memory, self.r[29]+4*i, 0xB5000000+i)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo, self.r[2] = 0xA5000010, 0xA5000011, u32(value)


def run(words):
    covered, count, paths = set(), 0, set()
    for c in cases():
        initial = fixture(c)
        want, calls = reference(initial, c)
        got = UpdateOracle(words, initial, c).run()
        assert public(got.memory) == public(want), (c, 'public memory')
        assert got.calls == calls, (c, 'call trace', got.calls, calls)
        covered.update(got.visits)
        paths.add(tuple(target for target, _ in calls))
        count += 1
    return dict(cases=count, visited_words=len(covered), call_paths=len(paths),
                original_provider_bodies_executed=False, hardware_or_gameplay_claim=False)
