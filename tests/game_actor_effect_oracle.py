"""Two-input effect dispatcher with effectful bounded helpers and typed sound calls."""
from tools.tests import test_game_quad_edge_emitter as edge
from tools.experiments import game_actor_effect_dispatch as source

STACK, put, read = edge.STACK, edge.put, edge.read
ACTOR = 0x24000
COUNTS = {source.FIRST: 2, source.SECOND: 3, source.THIRD: 3, source.SOUND: 5}


def fixture(kind=0x13, flags=0xABCDEF81):
    memory = {STACK+i: (i*17+0xA5) & 255 for i in range(-2048, 2048)}
    memory.update({ACTOR+i: (i*7+0xA5) & 255 for i in range(0x340)})
    put(memory, ACTOR, 1)
    memory[ACTOR+4] = kind
    return memory, (ACTOR, flags)


def reference(initial, args, phase=0):
    memory = dict(initial)
    put(memory, STACK+phase+4, args[1])
    kind, flags = read(memory, args[0]+4, 1), args[1] & 255
    if kind in (0x13, 0x23):
        return [(source.FIRST, args[0], flags), (source.SOUND, 0x69, args[0], 0x7D00, 200, 2000)]
    if kind == 0x1E:
        return [(source.SECOND, args[0], flags, 1)]
    if kind == 0x54:
        return [(source.THIRD, args[0], flags, 1)]
    return []


class EffectOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, fault=None, entry=source.ENTRY, bindings=None, connected=None):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault, entry=entry, connected=connected)
        self.bindings = bindings or {a: a for a in COUNTS}

    def record_call(self, target):
        canonical = self.bindings.get(target, target)
        args = self.arguments(COUNTS[canonical])
        self.calls.append((canonical, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        canonical = self.bindings.get(target, target)
        if self.mode and canonical != source.SOUND:
            self.put(self.input_args[0]+4, 0x54, 1)
            self.put(self.input_args[0], 5 if self.mode == 3 else 0, 4)
        for i in range(4):
            self.put(self.r[29]+4*i, 0xB5000000+i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000+i
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = 0xABCD0123
