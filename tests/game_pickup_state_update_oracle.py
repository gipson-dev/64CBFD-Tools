"""Independent public-state reference and bounded mutable helper contracts."""

from dataclasses import dataclass, replace
import math

from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating, signed


STATE, BANK, ALT, SELECTOR = 0x800D23B0, 0x20000, 0x22000, 0x80087340
ACTORS, END, DATA, ITEMS, EFFECTS = 0x800CC2D0, 0x800D121C, 0x30000, 0x26000, 0x28000
TICKS, SCALE = 0x800BE9E4, 0x8009DA90
MAP, EVENT, CLEAR, COLOR = 0x1508E780, 0x1508EB90, 0x1502EA50, 0x1502EA0C
SET, LIST, SPAWN, REMOVE = 0x15080620, 0x15033E28, 0x15083568, 0x15030158
CLEAN, RELEASE, OBJECT, RANDOM = 0x151027E8, 0x15060F28, 0x151149AC, 0x150ADA68
NODE, COORDS, DROP = 0x15086D48, 0x15086CBC, 0x1508DAEC
ARGUMENTS = {MAP: 1, EVENT: 3, CLEAR: 1, COLOR: 6, SET: 4, LIST: 2,
    SPAWN: 4, REMOVE: 2, CLEAN: 1, RELEASE: 2, OBJECT: 1, RANDOM: 0,
    NODE: 1, COORDS: 4, DROP: 2}


def narrow(value, width):
    mask = (1 << width) - 1
    return ((value & mask) ^ (1 << (width - 1))) - (1 << (width - 1))


def read(memory, address, size=4, signed_value=False):
    value = int.from_bytes(bytes(memory[address + i] for i in range(size)), 'big')
    return narrow(value, size * 8) if signed_value else value


def f32(value):
    return floating(bits(value))


def private(address):
    return STACK - 0x800 <= address < STACK + 0x100


@dataclass(frozen=True)
class Player:
    current: int = 0
    override: int = 0x457
    nausea: int = 0
    item: int = -1
    alternate: int = 0
    skip: int = 0
    status: int = 2
    charge: int = 0


@dataclass(frozen=True)
class Item:
    selector: int = 1
    timer: int = -1
    grace: int = 0
    flags: int = 0
    kind: int = 3
    owner: int = 0
    target: int = -1
    fixed: int = 0
    saved: tuple = (32768, -32769, 0x12345678)


@dataclass(frozen=True)
class Case:
    players: tuple = ()
    items: tuple = ()
    mode: int = 0
    selector: int = -1
    ticks: int = 1
    default: int = 0
    effects: tuple = ()
    effect_count: object = None
    animations: tuple = ((0, -1), (9, 0x1D), (20, 0x1028))
    random: tuple = (0.75, 0.25, 0.5)
    scale: float = 1.0
    targets: int = 3
    delay: int = 30
    node: int = 2
    coords: tuple = (-10.75, 32000.75, 65537.75)
    missing: tuple = ()
    cleanup: tuple = ()
    actions: tuple = ()


def initial(case):
    rows = [(STATE, BANK, 4), (SELECTOR, case.selector, 1), (TICKS, case.ticks, 4),
        (SCALE, bits(case.scale), 4)]
    for bank in (BANK, ALT):
        rows.extend(((bank + 0x10, len(case.players), 4), (bank + 0xEA4, len(case.items), 4),
            (bank + 0xEA8, case.targets, 4), (bank + 0xEAC, case.delay, 4),
            (bank + 0x1170, case.default, 4), (bank + 0x16BC, case.mode, 2)))
        for i in range(32):
            rows.extend(((bank + 0x10F0 + i * 4, -1, 4), (bank + 0x14F4 + i * 4, 100 + i, 4)))
        for i, p in enumerate(case.players):
            rows.extend(((bank + 0xEB0 + i * 4, p.item, 4), (bank + 0xFF0 + i * 4, p.override, 4)))
        for i, p in enumerate(case.items):
            for offset, value in ((0xEF0, p.selector), (0x1070, p.timer), (0x12F4, p.grace),
                    (0x11F4, p.flags), (0x1174, p.kind), (0x10F0, p.target), (0x1274, p.fixed),
                    (0x1374, p.saved[0]), (0x13F4, p.saved[1]), (0x1474, p.saved[2])):
                rows.append((bank + offset + i * 4, value, 4))
    for i in range(25):
        actor, data = ACTORS + i * 0x32C, DATA + i * 0x200
        rows.append((actor + 0x31C, data, 4))
        if i < len(case.players):
            p = case.players[i]
            rows.extend(((data + 0x75, p.current, 1), (data + 0x19B, p.nausea, 1),
                (data + 0x128, p.alternate, 1), (data + 0x11A, p.status, 1),
                (data + 0x19A, p.charge, 1), (data + 0x78, 0xA5, 1),
                (actor + 0x128, p.skip, 1), (actor + 0x125, 0xA5, 1)))
    for index, owner, identity in case.cleanup:
        a = ACTORS + index * 0x32C
        rows.extend(((a, 0x12340000, 4), (a + 0x65, owner, 1), (a + 4, identity, 1)))
    for i, item in enumerate(case.items):
        rows.extend(((ITEMS + i * 0x100 + 0x80, item.owner, 4), (ITEMS + i * 0x100 + 0x6E, 0xA5, 1)))
    rows.extend((EFFECTS + i * 0x80 + 6, value, 1) for i, value in enumerate(case.effects))
    return rows


def fixture(case):
    memory = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x800, 0x100)}
    for base, size in ((BANK, 0x1800), (ALT, 0x1800), (ACTORS, 25 * 0x32C),
            (DATA, 25 * 0x200), (ITEMS, 0x1000), (EFFECTS, 0x500),
            (STATE, 4), (SELECTOR, 1), (TICKS, 4), (SCALE, 4)):
        memory.update({base + i: 0 for i in range(size)})
    for address, value, size in initial(case):
        put(memory, address, value, size)
    return memory


def provider(case, target, args, occurrence):
    writes = [(a, v, n) for t, k, a, v, n in case.actions if (t, k) == (target, occurrence)]
    if target == MAP:
        result = dict(case.animations).get(signed(args[0]), signed(args[0]))
    elif target == LIST:
        result = len(case.effects) if case.effect_count is None else case.effect_count
    elif target == OBJECT:
        result = 0 if args[0] in case.missing else next((ITEMS + i * 0x100 for i, p in enumerate(case.items)
            if args[0] == (p.selector & 255)), 0)
    elif target == RANDOM:
        if occurrence >= len(case.random):
            raise AssertionError('Bounded random sequence exhausted')
        result = bits(case.random[occurrence])
    elif target == NODE:
        result = case.node
    else:
        result = 1 if target == COORDS else 0
    return result & 0xFFFFFFFF, writes


def public(memory):
    return {a: v for a, v in memory.items() if not private(a)}


def call_key(target, args):
    return (target, args[0]) if target in (LIST, COORDS) else (target, *args)


class UpdateOracle(TriangleOracle):
    def __init__(self, words, memory, case, phase=0):
        super().__init__(words, memory, phase, entry=0x1508DC24, arguments=())
        self.case, self.occurrences, self.fired = case, {}, []

    def record_call(self, target):
        self.calls.append(call_key(target, self.arguments(ARGUMENTS[target])))

    def hook(self, target):
        args = tuple(self.arguments(ARGUMENTS[target]))
        occurrence = self.occurrences.get(target, 0)
        self.occurrences[target] = occurrence + 1
        value, writes = provider(self.case, target, args, occurrence)
        if target == LIST:
            for i in range(len(self.case.effects)):
                self.put(args[1] + i * 4, EFFECTS + i * 0x80, 4)
        elif target == COORDS:
            for address, number in zip(args[1:], self.case.coords):
                self.put(address, bits(number), 4)
        for address, number, size in writes:
            self.fired.append((target, occurrence, address, number, size))
            self.put(address, number, size)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.condition = bool(len(self.calls) & 1)
        if target == RANDOM:
            self.f[0] = value
        else:
            self.r[2] = value

    def execute(self, word):
        if word >> 26 == 32:
            rs, rt = word >> 21 & 31, word >> 16 & 31
            offset = narrow(word, 16)
            self.r[rt] = narrow(self.get((self.r[rs] + offset) & 0xFFFFFFFF, 1), 8) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)


def reference(memory, case):
    m, calls, stores, occurrences, fired = memory.copy(), [], [], {}, []

    def get(a, n=4, sign=False):
        return read(m, a, n, sign)

    def store(a, value, n=4):
        put(m, a, value, n)
        stores.append(('W', a, n, value & ((1 << (n * 8)) - 1)))

    def call(target, *args):
        args = tuple(a & 0xFFFFFFFF for a in args)
        calls.append(call_key(target, args))
        k = occurrences.get(target, 0)
        occurrences[target] = k + 1
        value, writes = provider(case, target, args, k)
        for a, v, n in writes:
            fired.append((target, k, a, v, n))
            store(a, v, n)
        return signed(value)

    state, player = get(STATE), 0
    tables = {offset: state + offset for offset in
        (0xEB0, 0xEF0, 0xF70, 0xFF0, 0x1070, 0x10F0, 0x1174, 0x11F4,
         0x1274, 0x12F4, 0x1374, 0x13F4, 0x1474)}

    def address(offset, i):
        return tables[offset] + i * 4

    def value(offset, i):
        return get(address(offset, i), sign=True)

    count = get(state + 0x10, sign=True)
    entered = count > 0
    while player < count:
        assert player < 16, 'Outside bounded retail player tables'
        actor = ACTORS + player * 0x32C
        mode = get(state + 0x16BC, 2, True)
        if mode == 0xB9 and get(actor + 0x128, 1):
            player += 1
            continue
        data = get(actor + 0x31C)
        previous = get(data + 0x75, 1) & 127
        desired = value(0xFF0, player)
        nausea = get(data + 0x19B, 1)
        if nausea:
            desired = 58 if nausea >= 5 else 38
        if desired == 0:
            item = value(0xEB0, player)
            desired = value(0x1174, item) if item != -1 else get(state + 0x1170, sign=True)
        elif desired == 1111:
            desired = 0
        if mode == 184:
            previous = get(data + 0x128, 1) & ~32
        if desired != previous:
            animation = call(MAP, previous)
            if animation != -1:
                animation &= ~4096
                call(EVENT, player, 76, animation)
                if animation == 29:
                    call(EVENT, player, 76, 30)
                store(get(actor + 0x31C) + 0x11A, 0, 1)
            animation = call(MAP, desired)
            if animation >= 4097:
                call(EVENT, player, 75, animation & ~4096)
            if get(get(STATE) + 0x16BC, 2, True) == 184:
                if previous == 128:
                    call(CLEAR, actor)
                    store(actor + 0x125, 0, 1)
                store(get(actor + 0x31C) + 0x128, desired, 1)
                duration = {1: 600, 128: 1800, 16: 3}.get(desired)
                if duration is not None:
                    store(get(actor + 0x31C) + 0x12C, duration, 2)
                if desired == 128:
                    call(COLOR, actor, 0, 0, 255, 191, 4)
            else:
                call(SET, player, 1, desired, 0)
                if desired == 0 and previous != 3:
                    store(get(actor + 0x31C) + 0x78, 0, 1)
                if previous == 32:
                    call(EVENT, player, 69, 4)
                if desired == 32:
                    call(EVENT, player, 69, 3)
        state = get(STATE)
        if get(SELECTOR, 1, True) == player and get(state + 0x16BC, 2, True) != 184:
            animation = call(MAP, desired)
            n = call(LIST, actor, 0)
            found = False

            def spawn():
                call(SPAWN, actor, animation, bits(1.0), 0)
                if animation == 29:
                    call(SPAWN, actor, 30, bits(1.0), 0)

            if n == 0 and get(get(actor + 0x31C) + 0x11A, 1) == 2 and animation not in (85, 46):
                spawn()
            if n != 0 and desired != 32:
                if animation != -1:
                    animation &= ~4096
                    preserved = (42, 34, 45, 114, 115, 118, 119, 120, 7)
                else:
                    preserved = (42, 34, 44, 100, 45, 114, 115, 118, 119, 120, 7)
                for i in range(max(n, 0)):
                    effect = EFFECTS + i * 0x80
                    identity = get(effect + 6, 1)
                    keep = identity in preserved or animation != -1 and (
                        identity == animation or identity == 30 and animation == 29)
                    if not keep:
                        call(REMOVE, effect, 0)
                        store(get(actor + 0x31C) + 0x11A, 0, 1)
                    elif identity == animation:
                        found = True
                if animation != -1 and not found and get(get(actor + 0x31C) + 0x11A, 1) == 2 and animation not in (85, 46):
                    spawn()
            if animation != 85:
                start = get(get(STATE) + 0x10, sign=True)
                if start < 25:
                    for index in range(start, 25):
                        a = ACTORS + index * 0x32C
                        if get(a) and get(a + 0x65, 1) == player + 1 and get(a + 4, 1) == 110:
                            call(CLEAN, a)
                            call(RELEASE, a, 0)
                            break
            state = get(STATE)
        count = get(state + 0x10, sign=True)
        player += 1
    if entered:
        player = 0
    selected = narrow(get(SELECTOR, 1, True) + 1, 8)
    store(SELECTOR, selected, 1)
    if selected >= count:
        store(SELECTOR, 0, 1)
    index = 0
    limit = get(state + 0xEA4, sign=True)
    scale = floating(get(SCALE)) if limit > 0 else None
    while player < limit:
        assert index < 16, 'Outside bounded pickup corpus'
        item = call(OBJECT, get(address(0xEF0, index) + 3, 1))
        if item:
            if value(0x12F4, index) != 0:
                elapsed = narrow(value(0x12F4, index) - get(TICKS, sign=True), 32)
                store(address(0x12F4, index), elapsed)
                if elapsed <= 0:
                    store(address(0x1070, index), 4)
                    store(address(0x12F4, index), 0)
            timer = value(0x1070, index)
            if timer > 0:
                timer = narrow(timer - get(TICKS, sign=True), 32)
                store(address(0x1070, index), timer)
                if timer <= 0:
                    store(address(0x1070, index), 0)
                    store(item + 0x6E, 0, 1)
                    if value(0x12F4, index):
                        for axis, offset in enumerate((0x1374, 0x13F4, 0x1474)):
                            store(item + 0x10 + axis * 2, value(offset, index), 2)
                    elif not value(0x11F4, index) & 4:
                        if value(0x11F4, index) & 1:
                            width = f32(get(get(STATE) + 0xEA8, sign=True))
                            for _ in range(30):
                                random = floating(call(RANDOM) & 0xFFFFFFFF)
                                chosen = math.trunc(f32(f32(random * scale) * width))
                                n = get(get(STATE) + 0xEA8, sign=True)
                                if chosen not in [value(0x10F0, j) for j in range(max(n, 0))]:
                                    break
                            else:
                                raise AssertionError('Bounded random rejection exhausted')
                        else:
                            chosen = value(0x1274, index)
                        store(address(0x10F0, index), chosen)
                        node = call(NODE, get(get(STATE) + chosen * 4 + 0x14F4))
                        if node != -1:
                            call(COORDS, node, 0, 0, 0)
                            for axis, number in enumerate(case.coords):
                                store(item + 0x10 + axis * 2, math.trunc(f32(number)) + (60 if axis == 1 else 0), 2)
            elif timer == 0:
                owner = narrow(get(item + 0x80) - 1, 32)
                if owner != -1:
                    store(item + 0x80, 0)
                    actor = ACTORS + owner * 0x32C
                    if value(0x1174, index) == 2222:
                        data = get(actor + 0x31C)
                        store(data + 0x19A, get(data + 0x19A, 1) + 3, 1)
                        data = get(actor + 0x31C)
                        if get(data + 0x19A, 1) >= 7:
                            store(data + 0x19A, 6, 1)
                        store(address(0x1070, index), get(get(STATE) + 0xEAC))
                    else:
                        call(DROP, owner, 0)
                        if value(0x11F4, index) & 2:
                            store(address(0x1070, index), get(get(STATE) + 0xEAC))
                        else:
                            store(address(0x1070, index), -1)
                            store(address(0xF70, index), owner | 8192)
                            store(address(0x10F0, index), -1)
                        store(address(0x12F4, index), 0)
                        store(address(0xEB0, owner), player)
                        store(get(STATE) + owner * 4 + 0x5C, 1)
                    mode = get(get(STATE) + 0x16BC, 2, True)
                    if mode == 185:
                        store(get(actor + 0x31C) + 0x12C, 600, 2)
                        mode = get(get(STATE) + 0x16BC, 2, True)
                    if mode == 184:
                        data = get(actor + 0x31C)
                        kind = value(0x1174, index)
                        if kind == get(data + 0x128, 1) and kind in (1, 128, 16):
                            store(data + 0x12C, {1: 600, 128: 1800, 16: 3}[kind], 2)
        player += 1
        index += 1
        state = get(STATE)
        limit = get(state + 0xEA4, sign=True)
    return public(m), calls, stores, fired


def cases():
    for selector in (-128, -1, 0, 126, 127, 255):
        yield 'empty-selector-' + str(selector), Case(selector=selector)
    base = Case(players=(Player(),))
    for n in (1, 2, 4):
        yield 'players-' + str(n), replace(base, players=(Player(),) * n, selector=n - 1)
    for mode in (0, 0xB8, 0xB9, -1, -32768):
        for previous, desired in ((0, 0), (0, 1), (9, 20), (32, 0), (0, 32),
                (3, 0), (0, 128), (128, 16), (0, 1111), (0, 0x101), (0, -1)):
            p = Player(current=previous, alternate=previous, override=desired)
            yield 'transition-%d-%d-%d' % (mode, previous, desired), replace(base, mode=mode, players=(p,))
    for n in (0, 1, 4, 5, 255):
        yield 'nausea-' + str(n), replace(base, players=(Player(nausea=n),))
    yield 'skip-B9', replace(base, mode=0xB9, selector=0, players=(Player(skip=1),))
    yield 'skip-only-B9', replace(base, mode=0, players=(Player(skip=1),))
    yield 'selected-B8', replace(base, selector=0, mode=0xB8)
    yield 'B8-leave-128', replace(base, mode=0xB8, players=(Player(alternate=128, override=1),))
    yield 'default-kind', replace(base, default=9, players=(Player(override=0),))
    yield 'held-kind', replace(base, players=(Player(override=0, item=0),), items=(Item(kind=20),))
    for animation in (-1, 29, 32, 85, 46, 0x1055, 0x102E, 0x101D):
        for effects in ((), (30,), (29,), (44, 100), (42, 34, 45, 114, 115, 118, 119, 120, 7), (1, 2, 3)):
            p = Player(current=9, override=9)
            yield 'effects-%d-%s' % (animation, effects), replace(base, selector=0, players=(p,),
                effects=effects, animations=((9, animation),))
    yield 'negative-effect-count', replace(base, selector=0, effect_count=-1)
    yield 'negative-effect-count-mapped', replace(base, selector=0, effect_count=-2, animations=((0, 0x1042),))
    yield 'effect-skip-state32', replace(base, selector=0, players=(Player(current=32, override=32),), effects=(1, 2))
    yield 'cleanup-first-only', replace(base, selector=0, cleanup=((1, 1, 110), (2, 1, 110)))
    yield 'cleanup-last', replace(base, selector=0, cleanup=((1, 2, 110), (2, 1, 109), (24, 1, 110)))
    for ticks in (-2, 0, 1, 4, 20):
        for timer in (-2, -1, 0, 1, 4, 10):
            yield 'timer-%d-%d' % (ticks, timer), Case(items=(Item(timer=timer),), ticks=ticks)
        for grace in (-1, 1, 4, 10):
            yield 'grace-%d-%d' % (ticks, grace), Case(items=(Item(timer=1, grace=grace),), ticks=ticks)
    yield 'missing-object', Case(items=(Item(timer=1),), missing=(1,))
    yield 'selector-low-byte', Case(items=(Item(selector=0x123456FE, timer=1),))
    for flags in (0, 1, 2, 3, 4, 5, 6, 7, 0x80000000):
        yield 'respawn-flags-' + str(flags), Case(items=(Item(timer=1, flags=flags),))
    yield 'random-reject-used', Case(items=(Item(timer=1, flags=1, target=2),))
    yield 'node-not-found-minus-one', Case(items=(Item(timer=1),), node=-1)
    yield 'node-255-is-not-minus-one', Case(items=(Item(timer=1),), node=255)
    for mode in (0, 0xB8, 0xB9):
        for flags in (0, 2):
            for kind in (1, 16, 128, 2222):
                yield 'collect-%d-%d-%d' % (mode, flags, kind), Case(mode=mode,
                    players=(Player(alternate=kind, override=kind),), items=(Item(timer=0, owner=1, flags=flags, kind=kind),))
    for value in (0, 3, 4, 6, 250, 253, 254, 255):
        yield 'charge-wrap-' + str(value), Case(players=(Player(charge=value),),
            items=(Item(timer=0, owner=1, kind=2222),))
    yield 'owner-last-slot', Case(items=(Item(timer=0, owner=25),))
    yield 'multiple-items', Case(items=(Item(selector=1, timer=1), Item(selector=2, owner=2, timer=0),
        Item(selector=3, timer=1, grace=10)))
    # Helpers can redirect the global state without changing the captured tables.
    yield 'object-rebase-and-shorter-live-count', Case(items=(Item(timer=0, owner=1, flags=2), Item(selector=2)),
        actions=((OBJECT, 0, STATE, ALT, 4), (OBJECT, 0, ALT + 0xEAC, 1234, 4),
                 (OBJECT, 0, ALT + 0xEA4, 0, 4)))
    yield 'map-mode-switch', replace(base, players=(Player(current=9, override=128),),
        actions=((MAP, 0, BANK + 0x16BC, 184, 2),))
    yield 'map-data-rebind', replace(base, players=(Player(current=9, override=20),),
        actions=((MAP, 0, ACTORS + 0x31C, DATA + 0x200, 4),))
    yield 'list-shorter-player-count', replace(base, selector=0,
        actions=((LIST, 0, BANK + 0x10, 0, 4),))
    yield 'drop-flags-mutation', Case(items=(Item(timer=0, owner=1),),
        actions=((DROP, 0, BANK + 0x11F4, 2, 4),))
    yield 'random-live-count-change', Case(items=(Item(timer=1, flags=1),),
        actions=((RANDOM, 0, BANK + 0xEA8, 0, 4),))
    yield 'object-scale-mutation-cached', Case(items=(Item(timer=1, flags=1),),
        actions=((OBJECT, 0, SCALE, bits(0.0), 4),))
    yield 'node-public-coordinate-alias', Case(items=(Item(timer=1),),
        actions=((COORDS, 0, ITEMS + 0x12, 0x1234, 2),))


def native_harness(body, corpus):
    regions = ((BANK, 0x1800), (ALT, 0x1800), (ACTORS, 25 * 0x32C),
        (DATA, 25 * 0x200), (ITEMS, 0x1000), (EFFECTS, 0x500),
        (STATE, 4), (SELECTOR, 1), (TICKS, 4), (SCALE, 4))
    offsets, total = [], 0
    for _, size in regions:
        total = (total + 31) & ~15
        offsets.append(total)
        total += size
    total = (total + 31) & ~15
    patches, calls, rows = [], [], []
    pointer_args = {CLEAR: (0,), COLOR: (0,), LIST: (0,), SPAWN: (0,),
        REMOVE: (0,), CLEAN: (0,), RELEASE: (0,)}

    def literal(a, v, n):
        pointer = a == STATE or ACTORS <= a < END and (a - ACTORS) % 0x32C == 0x31C
        opaque = n == 4 and any(b + 0xEF0 <= a < b + 0xF70 for b in (BANK, ALT))
        return '{0x%Xu,0x%Xu,%d,%d}' % (a, v & 0xFFFFFFFF, n, 1 if pointer else 2 if opaque else 0)

    for _, case in corpus:
        _, expected_calls, expected_stores, _ = reference(fixture(case), case)
        first = len(patches)
        patches.extend(literal(*p) for p in initial(case))
        count = len(patches) - first
        wanted = len(patches)
        patches.extend(literal(a, v, n) for _, a, n, v in expected_stores)
        written = len(patches) - wanted
        call_first, occurrences = len(calls), {}
        for target, *args in expected_calls:
            k = occurrences.get(target, 0)
            occurrences[target] = k + 1
            result, writes = provider(case, target, args, k)
            begin = len(patches)
            patches.extend(literal(*p) for p in writes)
            mask = sum(1 << i for i in pointer_args.get(target, ()))
            calls.append('{0x%Xu,%d,%d,{%s},0x%Xu,%d,%d}' % (target, len(args), mask,
                ','.join('0x%Xu' % (a & 0xFFFFFFFF) for a in (*args, *((0,) * (6 - len(args))))),
                result, begin, len(patches) - begin))
        coords = ','.join('0x%Xu' % bits(v) for v in case.coords)
        effects = ','.join('0x%Xu' % (EFFECTS + i * 0x80) for i in range(len(case.effects))) or '0'
        rows.append('{%d,%d,%d,%d,%d,%d,%d,{%s},{%s}}' % (
            first, count, wanted, written, call_first, len(expected_calls), len(case.effects), coords, effects))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++){
 if(a>=regions[i][0]&&a-regions[i][0]<=regions[i][1]){return b+regions[i][2]+a-regions[i][0];}}fail(29);}
struct Patch{u32 a,v,n,kind;};static const struct Patch patches[]={PATCHES};
struct Call{u32 target,n,mask,a[6],result,first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,call_first,call_count,effect_count,coords[3],effects[10];};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 ordinal;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static void apply(u8*b,u32 first,u32 count){u32 i,j,v;const struct Patch*q;u8*p;
 for(i=0;i<count;i++){q=patches+first+i;v=q->kind==1?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->kind==2)for(j=0;j<q->n;j++)p[j]=(u8)(v>>(8*(q->n-1-j)));
 else if(q->n==1)*p=(u8)v;else if(q->n==2)*(s16*)p=(s16)v;else*(u32*)p=v;}}
static u32 invoke(u32 target,u32 n,const u32*a){u32 i,v;const struct Call*q;
 if(ordinal>=c->call_count){fail(22);}q=calls+c->call_first+ordinal++;
 if(target!=q->target||n!=q->n){fail(22);}for(i=0;i<n;i++){v=q->a[i];if(q->mask&(1u<<i))v=(u32)address(v,actual);if(a[i]!=v)fail(23);}
 apply(actual,q->first,q->count);return q->result;}
#define D_800D23B0 (*(s32*)address(0x800D23B0u,actual))
#define D_800CC2D0 address(0x800CC2D0u,actual)
#define D_800D121C address(0x800D121Cu,actual)
#define D_80087340 (*(s8*)address(0x80087340u,actual))
#define D_800BE9E4 (*(s32*)address(0x800BE9E4u,actual))
#define D_8009DA90 (*(f32*)address(0x8009DA90u,actual))
s32 func_1508E780(s32 s){u32 a[]={(u32)s};return invoke(0x1508E780u,1,a);}
s32 func_1508EB90(s32 p,s32 e,s32 v){u32 a[]={(u32)p,(u32)e,(u32)v};return invoke(0x1508EB90u,3,a);}
void func_1502EA50(u8*p){u32 a[]={(u32)p};invoke(0x1502EA50u,1,a);}
void func_1502EA0C(u8*p,s32 r,s32 g,s32 b,s32 a0,s32 mode){u32 a[]={(u32)p,r,g,b,a0,mode};invoke(0x1502EA0Cu,6,a);}
void func_15080620(s32 p,s32 m,s32 s,s32 v){u32 a[]={p,m,s,v};invoke(0x15080620u,4,a);}
s32 func_15033E28(u8*p,u8**out){u32 i,a[]={(u32)p};for(i=0;i<c->effect_count;i++)out[i]=address(c->effects[i],actual);return invoke(0x15033E28u,1,a);}
u8*func_15083568(u8*p,s32 animation,f32 scale,s32 m){u32 a[]={(u32)p,animation,word(scale),m};invoke(0x15083568u,4,a);return 0;}
void func_15030158(u8*p,s32 m){u32 a[]={(u32)p,m};invoke(0x15030158u,2,a);}
void func_151027E8(u8*p){u32 a[]={(u32)p};invoke(0x151027E8u,1,a);}
void func_15060F28(u8*p,s32 m){u32 a[]={(u32)p,m};invoke(0x15060F28u,2,a);}
u8*func_151149AC(u8 id){u32 a[]={id},v=invoke(0x151149ACu,1,a);return v?address(v,actual):0;}
f32 func_150ADA68(void){return real(invoke(0x150ADA68u,0,0));}
s32 func_15086D48(s32 key){u32 a[]={key};return invoke(0x15086D48u,1,a);}
s32 func_15086CBC(s32 id,f32*x,f32*y,f32*z){u32 a[]={id};*x=real(c->coords[0]);*y=real(c->coords[1]);*z=real(c->coords[2]);return invoke(0x15086CBCu,1,a);}
s32 func_1508DAEC(s32 p,s32 m){u32 a[]={p,m};return invoke(0x1508DAECu,2,a);}
BODY
__attribute__((force_align_arg_pointer)) void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;ordinal=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 func_1508DC24();if(ordinal!=c->call_count)fail(25);for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(24);
 }fail(0);}
'''.replace('SIZE', str(total)).replace('REGIONS', ','.join(
        '{0x%Xu,%d,%d}' % (a, n, o) for (a, n), o in zip(regions, offsets))).replace(
        'PATCHES', ','.join(patches)).replace('CALLS', ',\n'.join(calls)).replace(
        'CASES', ',\n'.join(rows)).replace('BODY', body)
