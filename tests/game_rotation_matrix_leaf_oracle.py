"""Retail matrix formula, exact finite trig reduction and bounded guest execution."""
from tools.experiments import game_rotation_matrix_leaf as source
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_actor_world_matrix_oracle as world
from tools.tests.game_fixed_matrix_oracle import integer
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

STACK, OUTPUT = machine.STACK, 0x24000
COS, SIN, FACTOR, COEFFICIENTS = 0x150AD780, 0x150AD78C, 0x8009F6C0, 0x8009F710
DEGREES = (-720.0, -360.0, -180.0, -90.0, -45.0, -0.01, -0.0, 0.0, 0.01, 30.0, 45.0, 90.0, 180.0, 720.0)
RETURNS = (0.0, -0.0, 1.0, -1.0, 0.25, -0.5, 0.75, -0.125)


def fixture(constants, phase=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x600, 0x100)}
    memory.update({OUTPUT + i: (i * 13 + 0x5A) & 255 for i in range(-32, 128)})
    for address, value in constants.items():
        put(memory, address, value)
    return memory


def angles(index):
    return tuple(bits(DEGREES[(index * step + offset) % len(DEGREES)]) for step, offset in ((1, 0), (3, 1), (5, 2)))


def provider(index, ordinal):
    return bits(RETURNS[(index + ordinal * 3) % len(RETURNS)])


def trig(word, target, constants):
    if target == COS:
        word = fp(word, constants[COEFFICIENTS], 'add')
    exponent = (word >> 22) & 0x1FF
    if exponent < 0xFF:
        if exponent < 0xE6:
            return word
        square = fp(word, word, 'mul')
        polynomial = constants[COEFFICIENTS + 4]
        for offset in (8, 12, 16):
            polynomial = fp(constants[COEFFICIENTS + offset], fp(polynomial, square, 'mul'), 'add')
        return fp(fp(polynomial, fp(square, word, 'mul'), 'mul'), word, 'add')
    if exponent >= 0x136:
        return 0
    quotient = integer(fp(constants[COEFFICIENTS + 20], word, 'mul'), 0)
    whole = bits(float(signed(quotient)))
    reduced = fp(word, fp(constants[COEFFICIENTS + 24], whole, 'mul'), 'sub')
    reduced = fp(reduced, fp(constants[COEFFICIENTS + 28], whole, 'mul'), 'sub')
    square = fp(reduced, reduced, 'mul')
    polynomial = constants[COEFFICIENTS + 32]
    for offset in (36, 40, 44):
        polynomial = fp(constants[COEFFICIENTS + offset], fp(polynomial, square, 'mul'), 'add')
    result = fp(fp(fp(polynomial, square, 'mul'), reduced, 'mul'), reduced, 'add')
    return result ^ (0x80000000 if quotient & 1 else 0)


def matrix(values):
    cosR, sinR, cosP, sinP, cosH, sinH = values
    productR, productS = fp(sinR, sinP, 'mul'), fp(cosR, sinP, 'mul')
    return [fp(cosP, cosH, 'mul'), fp(cosP, sinH, 'mul'), sinP ^ 0x80000000, 0,
        fp(fp(productR, cosH, 'mul'), fp(cosR, sinH, 'mul'), 'sub'),
        fp(fp(productR, sinH, 'mul'), fp(cosR, cosH, 'mul'), 'add'), fp(sinR, cosP, 'mul'), 0,
        fp(fp(productS, cosH, 'mul'), fp(sinR, sinH, 'mul'), 'add'),
        fp(fp(productS, sinH, 'mul'), fp(sinR, cosH, 'mul'), 'sub'), fp(cosR, cosP, 'mul'), 0,
        0, 0, 0, bits(1.0)]


def reference(memory, arguments, index=0, actual=False):
    calls, values = [], []
    factor = read(memory, FACTOR)
    constants = {address: read(memory, address) for address in (FACTOR, *range(COEFFICIENTS, COEFFICIENTS + 48, 4))}
    for angle in arguments[1:]:
        scaled = fp(angle, factor, 'mul')
        for target in (COS, SIN):
            calls.append((target, scaled))
            values.append(trig(scaled, target, constants) if actual else provider(index, len(values)))
    return matrix(values), calls


class RotationOracle(machine.BurstOracle):
    def __init__(self, words, memory, arguments, phase=0, index=0, mode=0, connected=None,
                 entry=source.ENTRY, fault=None):
        super().__init__(words, memory, phase=phase, entry=entry, connected=connected,
            arguments=arguments, fault=fault)
        self.index, self.mode = index, mode
        self.current_pc = self.delay_of = None
        self.code = faults.TrackedCode(self.code, self)

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 36:
            self.dispatched_word, self.own_instruction = word, True
            try:
                self.f[word >> 6 & 31] = integer(self.f[word >> 11 & 31], 0)
            finally:
                self.own_instruction = False
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in (COS, SIN)
        args = (self.f[12],)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target in (COS, SIN)
        result = provider(self.index, len(self.calls) - 1)
        if self.mode and len(self.calls) == 1:
            # The declared leaf provider may mutate data, but never owns the parent's homes.
            put(self.memory, FACTOR, bits(0.5))
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.f[0] = result


def state(instance):
    return (instance.r, instance.f, instance.memory, instance.events, instance.calls, instance.lo,
            instance.hi, instance.condition, instance.current_pc, instance.delay_of, instance.accesses)


def orientation(memory, arguments):
    values, _ = reference(memory, arguments, actual=True)
    return values


def builder_reference(memory):
    memory = dict(memory)
    inputs = tuple(read(memory, world.ACTOR + i * 4) for i in range(3))
    first = orientation(memory, (OUTPUT, 0, inputs[1], 0))
    second = orientation(memory, (OUTPUT + 64, inputs[0], 0, inputs[2]))
    for base, values in ((OUTPUT, first), (OUTPUT + 64, second)):
        for i, value in enumerate(values):
            put(memory, base + i * 4, value)
    world.product.multiply(memory, OUTPUT + 64, OUTPUT, OUTPUT)
    for offset, position in ((48, 0x10), (56, 0x14)):
        put(memory, OUTPUT + offset, bits(float(world.signed16(read(memory, world.ACTOR + position, 2)))))
    put(memory, OUTPUT + 52, fp(read(memory, world.ACTOR + 0x18),
        bits(float(world.signed16(read(memory, world.ACTOR + 0x12, 2)))), 'add'))
    scales = tuple(read(memory, world.ACTOR + at) for at in (0x2C, 0x30, 0x34))
    world.scale_matrix(memory, OUTPUT + 64, scales)
    world.product.multiply(memory, OUTPUT + 64, OUTPUT, OUTPUT)
    return [read(memory, OUTPUT + i * 4) for i in range(16)]


class ChainOracle(RotationOracle):
    def record_call(self, target):
        if target in (COS, SIN):
            return super().record_call(target)
        counts = {world.ANGLES: 2, world.SCALE: 4, world.MULTIPLY: 3, source.ENTRY: 4,
                  world.LOOKUP: 1, world.POINT: 7, world.source.ENTRY: 2}
        args = self.arguments(counts[target])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        raise AssertionError(('Unconnected matrix-chain provider', hex(target)))
