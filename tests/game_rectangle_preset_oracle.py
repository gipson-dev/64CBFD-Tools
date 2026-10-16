"""Independent thirteen-word argument contract for rectangle preset dispatch."""
from tools.tests import test_game_quad_edge_emitter as edge
from tools.experiments import game_rectangle_preset_dispatch as source

STACK, put, read, bits = edge.STACK, edge.put, edge.read, edge.bits
ACTOR = 0x24000
PRESETS = {
    0xEB: (400., 500., 0., None, 0., 2, 5, 20, 20, 1.),
    0xF6: (200., 400., -1800., -1000., -1200., 2, 5, 4, 10, 1.),
    0xF8: (100., 160., -2500., None, 0., 2, 5, 4, 4, .5),
    0xF9: (200., 100., 100., -300., 0., 1, 5, 4, 4, 1.),
}


def fixture(rom, selector=0xEB, flags=0xABCDEF81, context=0x87654321, pattern=0):
    memory = {STACK+i: (i*17+0xA5) & 255 for i in range(-2048, 2048)}
    memory.update({ACTOR+i: (i*7+0xA5) & 255 for i in range(128)})
    memory[ACTOR+0x72] = selector
    memory.update({0x800A6FC0+i: b for i, b in enumerate(rom[0x24BA80:0x24BA88])})
    if pattern:
        put(memory, 0x800A6FC0, (0x80000000, bits(17.25), 0x7FC12345)[(pattern-1) % 3])
        put(memory, 0x800A6FC4, (bits(-123.5), 0x80000000, 0x7F800000)[(pattern-1) % 3])
    return memory, (ACTOR, flags, context)


def reference(memory, args, phase=0):
    memory = dict(memory)
    put(memory, STACK+phase+4, args[1])
    put(memory, STACK+phase+8, args[2])
    kind = read(memory, args[0]+0x72, 1)
    if kind not in PRESETS:
        return []
    p = list(PRESETS[kind])
    values = [bits(x) for x in p[:5] if x is not None]
    # Offsets are live bit-preserving loads, not a synthetic preset table.
    if kind in (0xEB, 0xF8):
        values.insert(3, read(memory, 0x800A6FC0 if kind == 0xEB else 0x800A6FC4))
    return [(source.CALLEE, args[0], *values, *p[5:9], bits(p[9]), args[1] & 255, args[2])]


class DispatchOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, fault=None, entry=source.ENTRY, bindings=None, connected=None):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault, entry=entry, connected=connected)
        self.bindings = bindings or {source.CALLEE: source.CALLEE}

    def record_call(self, target):
        canonical = self.bindings.get(target, target)
        if canonical != source.CALLEE:
            raise AssertionError(('unexpected preset callee', hex(target)))
        args = self.arguments(13)
        self.calls.append((canonical, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if self.mode:
            self.put(self.input_args[0]+0x72, 0x5A, 1)
            self.put(0x800A6FC0, bits(999.0), 4)
            self.put(0x800A6FC4, bits(777.0), 4)
        for i in range(4):
            self.put(self.r[29]+4*i, 0xB5000000+i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000+i
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = 0xAABBCCDD
