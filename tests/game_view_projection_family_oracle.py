"""Bounded matrix-call protocol model, not a replacement for the SDK or FCSR."""
from tools.tests import test_game_view_projection_command as parent
from tools.tests import test_game_cosine_match as cosine
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits

PAGE, PERSPECTIVE, FIXED = 0x800BE9C0, 0x15047F00, 0x150A7790
PARENT, CHILD, WRAPPER = parent.ENTRY, parent.CHILD, parent.WRAPPER
BASE, VIEWS, ALTERNATE, THIRD = parent.BASE, parent.VIEWS, parent.ALTERNATE, parent.THIRD
FIELDS = (0xC, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x6C, 0x70, 0x74, 0x78, 0x7C, 0x80)
NUMERIC = set(FIELDS) | set(range(0xBC, 0xFC, 4)) | set(range(0x100, 0x180, 4))
GLOBALS = (parent.COEF_X, parent.COEF_Y, parent.FOV_OVERRIDE, parent.NEAR_OVERRIDE,
    parent.FAR_OVERRIDE, parent.NEAR_DEFAULT, parent.FAR_DEFAULT)


def store(memory, address, word, size=4):
    for i, value in enumerate((word & ((1 << (size * 8)) - 1)).to_bytes(size, 'big')):
        memory[(address + i) & 0xFFFFFFFF] = value


def fixture(index=0, near=0, far=0, page=0):
    memory = parent.fixture(index, near, far)
    memory[PAGE] = page
    for region, base in enumerate((VIEWS, ALTERNATE, THIRD)):
        for slot in range(6):
            record = base + slot * 0x180
            store(memory, record + 0xB8, 0xA55A, 2)
            for j in range(16):
                put(memory, record + 0xBC + j * 4, bits((j + 1) * 0.125 + slot + region))
            for j in range(32):
                put(memory, record + 0x100 + j * 4, 0x11223300 + region * 0x1000 + slot * 0x100 + j)
            for high_page in (128, 129, 254, 255):
                for i in range(64):
                    address = record + 0x100 + high_page * 64 + i
                    memory.setdefault(address, (i * 13 + 0xA5) & 255)
    return memory


def perspective_effect(memory, args, mode):
    matrix, normalization, y, x, near, far, scale = args
    for j in range(16):
        put(memory, matrix + j * 4, 0x3F000000 | ((y ^ x ^ near ^ far ^ scale ^ (j * 0x10203)) & 0x7FFFFF))
    if normalization:
        store(memory, normalization, 0x8000 if mode == 3 else 0x8000 | ((y ^ near ^ scale) & 0x7FFF), 2)
    if mode == 1:
        put(memory, BASE, THIRD)
        memory[PAGE] = 1
    elif mode == 2:
        memory[PAGE] ^= 1


def fixed_effect(memory, args):
    source, destination = args
    values = [read(memory, source + j * 4) ^ (0x01010101 * (j + 1)) for j in range(16)]
    for j, value in enumerate(values):
        address = (destination + j * 4) & 0xFFFFFFFF
        assert all(address + i in memory for i in range(4)), 'Unowned mock matrix output'
        put(memory, address, value)


def child_reference(memory, args, mode=0):
    memory, calls = dict(memory), []
    index, normalization, y, x, near, far, scale = args
    offset = index * 0x180 & 0xFFFFFFFF
    first = ((read(memory, BASE) + offset + 0xBC) & 0xFFFFFFFF, normalization, y, x, near, far, scale)
    calls.append((PERSPECTIVE, first))
    perspective_effect(memory, first, mode)
    base = read(memory, BASE)
    second = ((base + offset + 0xBC) & 0xFFFFFFFF, (base + offset + memory[PAGE] * 64 + 0x100) & 0xFFFFFFFF)
    calls.append((FIXED, second))
    fixed_effect(memory, second)
    return memory, calls


def reference(memory, args, trig_mode=0, sdk_mode=0, seed=0, root=PARENT):
    if root == CHILD:
        result, calls = child_reference(memory, args, sdk_mode)
        return parent.external(result), calls
    arguments = (*args, 0) if root == WRAPPER else args
    result, calls = parent.reference(memory, arguments, seed, trig_mode)
    result, sdk = child_reference(result, calls[-1][1], sdk_mode)
    calls += sdk
    if root == WRAPPER:
        index, x, y, scale = args
        for offset, value in ((0, scale), (4, x), (8, y)):
            put(result, 0x800D9AC0 + index * 12 + offset, value)
        result[0x800D9AF0] = 1
    return parent.external(result), calls


class FamilyOracle(parent.CommandOracle):
    def __init__(self, words, memory, args, trig_mode=0, sdk_mode=0, seed=0, phase=0, root=PARENT,
                 connected=None, fault=None):
        super().__init__(words, memory, args, seed, trig_mode, phase, connected=connected, entry=root, fault=fault)
        self.sdk_mode = sdk_mode

    def execute(self, word):
        # LB is used by the compiled signed-page negative, not the positive body.
        if word >> 26 == 32:
            rs, rt = word >> 21 & 31, word >> 16 & 31
            immediate = word & 65535
            address = (self.r[rs] + (immediate if immediate < 32768 else immediate - 65536)) & 0xFFFFFFFF
            self.own_instruction = True
            try:
                value = self.get(address, 1)
            finally:
                self.own_instruction = False
            self.r[rt] = (value if value < 128 else value - 256) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def access(self):
        if self.own_instruction and (PARENT <= self.current_pc < PARENT + 516 or CHILD <= self.current_pc < CHILD + 152):
            if self.root_accesses == self.root_fault:
                raise parent.faults.AccessBoundary
            self.root_accesses += 1

    def record_call(self, target):
        if target == PARENT:
            self.command_calls.append(self.arguments(5))
            return
        if target in (trig.ENTRY, cosine.ENTRY):
            args = (self.f[12],)
        else:
            assert target in (CHILD, PERSPECTIVE, FIXED), hex(target)
            args = self.arguments(2 if target == FIXED else 7)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        ordinal = sum(t in (trig.ENTRY, cosine.ENTRY) for t, _ in self.calls)
        value = None
        if target in (trig.ENTRY, cosine.ENTRY):
            parent.effects(self.memory, self.index, ordinal, self.mode)
            value = parent.RESULTS[(self.seed + ordinal * 3) % len(parent.RESULTS)]
        elif target == PERSPECTIVE:
            perspective_effect(self.memory, self.calls[-1][1], self.sdk_mode)
        else:
            assert target == FIXED
            fixed_effect(self.memory, self.calls[-1][1])
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344 + len(self.calls)
        if value is not None:
            self.f[0] = value
