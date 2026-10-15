"""Ordered matrix-builder contracts and original/current helper connections."""
import math

from tools.experiments import game_actor_world_matrix as source
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_view_matrix_pass_oracle as product
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating

ACTOR, OUTPUT, OBJECT = 0x22000, 0x24000, 0x20000
ANGLES, SCALE, MULTIPLY, ROTATE = 0x151148A8, 0x150A7CB0, 0x150A7A48, 0x150A8050
POSITION, LOOKUP, POINT, CATEGORY = 0x1511F31C, 0x151149AC, 0x150A7960, 0x800BE9F0
COORDINATES = (-32768, -1, 0, 1, 32767)
SCALES = (0.0, -0.0, 1.0, -1.0, 0.5, 2.0)
HEIGHTS = (0.0, -0.0, 0.5, -0.75, 32768.0)


def signed16(value):
    return value - 65536 if value & 32768 else value


def external(memory):
    return {a: b for a, b in memory.items() if not STACK - 0x600 <= a < STACK + 0x100}


def fixture(pattern=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x600, 0x100)}
    for base in (ACTOR, OUTPUT, OBJECT):
        memory.update({base + i: (i * 13 + 0x5A) & 255 for i in range(-16, 192)})
    for i in range(3):
        put(memory, ACTOR + i * 4, bits((pattern + i) * 0.25))
        put(memory, ACTOR + 0x10 + i * 2, COORDINATES[(pattern + i * 2) % 5] & 65535, 2)
        put(memory, ACTOR + 0x2C + i * 4, bits(SCALES[(pattern + i * 2) % 6]))
    put(memory, ACTOR + 0x18, bits(HEIGHTS[pattern % 5]))
    put(memory, OBJECT + 0x54, 0x8005, 2)
    put(memory, OBJECT + 0x3E, 0xAB81, 2)
    put(memory, CATEGORY, 0x35)
    return memory


def leaf(pattern, ordinal):
    return [bits(1.0 if i == 15 else 0.0 if i >= 12 or i % 4 == 3 else
                 (((i * 3 + pattern + ordinal * 2) % 7) - 3) * 0.25) for i in range(16)]


def orientation(pattern):
    memory = {}
    for base, values in ((0, leaf(pattern, 1)), (64, leaf(pattern, 0))):
        for i, value in enumerate(values):
            put(memory, base + i * 4, value)
    product.multiply(memory, 0, 64, 128)
    return [read(memory, 128 + i * 4) for i in range(16)]


def angles_effect(memory, mode):
    if mode == 1:
        for i, value in enumerate((-123, 456, -789)):
            put(memory, ACTOR + 0x10 + i * 2, value & 65535, 2)
            put(memory, ACTOR + 0x2C + i * 4, bits((i + 1) * 0.5))
        put(memory, ACTOR + 0x18, bits(-3.75))


def scale_effect(memory, mode, destination):
    if mode == 2:
        put(memory, destination, bits(7.0))
        put(memory, ACTOR + 0x2C, bits(9.0))


def scale_matrix(memory, destination, values):
    for i in range(16):
        put(memory, destination + i * 4, values[i // 5] if i in (0, 5, 10) else bits(1.0) if i == 15 else 0)


def reference(memory, pattern=0, mode=0, destination=OUTPUT, incoming=STACK):
    memory = dict(memory)
    scale = incoming - 96 + 32
    calls = [(ANGLES, destination, ACTOR)]
    for i, value in enumerate(orientation(pattern)):
        put(memory, destination + i * 4, value)
    angles_effect(memory, mode)
    put(memory, destination + 48, bits(float(signed16(read(memory, ACTOR + 0x10, 2)))))
    value = floating(read(memory, ACTOR + 0x18)) + signed16(read(memory, ACTOR + 0x12, 2))
    put(memory, destination + 52, bits(value))
    put(memory, destination + 56, bits(float(signed16(read(memory, ACTOR + 0x14, 2)))))
    values = tuple(read(memory, ACTOR + at) for at in (0x2C, 0x30, 0x34))
    calls.append((SCALE, scale, *values))
    scale_matrix(memory, scale, values)
    scale_effect(memory, mode, destination)
    calls.append((MULTIPLY, scale, destination, destination))
    product.multiply(memory, scale, destination, destination)
    return memory, calls


def position_reference(memory, pattern, phase):
    matrix = STACK + phase - 144 + 72
    memory, _ = reference(memory, pattern=pattern, destination=matrix, incoming=STACK + phase - 144)
    fp = product.family.parent.fp
    inputs = tuple(map(bits, (-3.0, 223.0, 549.0)))
    for axis in range(3):
        terms = [fp(read(memory, matrix + (axis + row * 4) * 4), inputs[row], 'mul') for row in range(3)]
        result = fp(fp(terms[0], terms[1], 'add'),
                    fp(terms[2], read(memory, matrix + (axis + 12) * 4), 'add'), 'add')
        put(memory, OBJECT + 0x10 + axis * 2, math.trunc(floating(result)) & 65535, 2)
    return memory


class WorldMatrixOracle(machine.MaskOracle):
    def __init__(self, words, memory, pattern=0, mode=0, destination=OUTPUT, phase=0,
                 connected=None, fault=None, entry=source.ENTRY, arguments=None):
        super().__init__(words, memory, phase=phase, entry=entry,
            arguments=arguments or (destination, ACTOR), connected=connected, fault=fault)
        self.pattern, self.mode, self.leaf_calls = pattern, mode, 0
        self.current_pc = self.delay_of = None
        self.code = faults.TrackedCode(self.code, self)

    def record_call(self, target):
        counts = {ANGLES: 2, SCALE: 4, MULTIPLY: 3, ROTATE: 4, LOOKUP: 1, source.ENTRY: 2, POINT: 7}
        args = self.arguments(counts[target])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        args = self.calls[-1][1:]
        result = None
        if target == ANGLES:
            assert args[1] == ACTOR
            for i, value in enumerate(orientation(self.pattern)):
                self.put(args[0] + i * 4, value, 4)
            angles_effect(self.memory, self.mode)
        elif target == SCALE:
            scale_matrix(self.memory, args[0], args[1:])
            destination = next(call[1] for call in self.calls if call[0] == ANGLES)
            scale_effect(self.memory, self.mode, destination)
        elif target == MULTIPLY:
            product.multiply(self.memory, *args)
        elif target == ROTATE:
            ordinal = self.leaf_calls
            assert ordinal in (0, 1)
            wanted = (0, read(self.memory, ACTOR + 4), 0) if ordinal == 0 else (
                read(self.memory, ACTOR), 0, read(self.memory, ACTOR + 8))
            assert args[1:] == wanted
            for i, value in enumerate(leaf(self.pattern, ordinal)):
                self.put(args[0] + i * 4, value, 4)
            self.leaf_calls += 1
        elif target == LOOKUP:
            assert args == (0x81,)
            result = ACTOR
        else:
            raise AssertionError(('Unexpected opaque matrix provider', hex(target)))
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        if result is not None:
            self.r[2] = result


def state(instance):
    return (instance.r, instance.f, instance.memory, instance.events, instance.calls,
            instance.lo, instance.condition, instance.current_pc, instance.delay_of, instance.accesses)
