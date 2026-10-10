"""Actual helper bodies and an independent public renderer reference adapter."""
import struct
from unittest.mock import patch

from tools.tests import test_game_actor_renderer_recovery as renderer
from tools.tests import test_game_actor_render_dispatch_recovery as dispatch
from tools.tests import test_game_actor_alpha_shading_match as shading
from tools.tests import test_game_object_color_mode_recovery as fog
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.experiments import game_actor_renderer_matching as matching

COLOR, FOG, IDENTITY, FLOAT_IDENTITY, PACK = 0x1502CC34, 0x1502EC34, 0x151EFE88, 0x151EFE00, 0x151EFD00
CALLER, RGB, SHADING, POINT, WRAPPER, CONTINUATION = (
    0x1502C974, 0x1502D54C, 0x1502D630, 0x150A7960, 0x150A7A00, 0x150A7A14)
PRIMITIVE, ENVIRONMENT, FLOAT = 0x800D9B68, 0x800D9B78, 0x2F000
HELPERS = ((COLOR, 0x5A0E4, 50), (FOG, 0x5C0E4, 150),
    (CALLER, 0x59E24, 176), (RGB, 0x5A9FC, 57), (SHADING, 0x5AAE0, 125),
    (POINT, 0xD4E10, 40), (WRAPPER, 0xD4EB0, 5), (CONTINUATION, 0xD4EC4, 13),
    (PACK, 0x21D1B0, 64), (FLOAT_IDENTITY, 0x21D2B0, 34), (IDENTITY, 0x21D338, 12))
ACTUAL = {entry for entry, _, _ in HELPERS} | {renderer.screen.ENTRY}
IDENTITY_WORDS = (0x00010000, 0, 1, 0, 0, 0x00010000, 0, 1, *([0] * 8))
INNER_COUNTS = {FOG: 5, FLOAT_IDENTITY: 1, PACK: 2, WRAPPER: 8}


def load_helpers(root):
    rom = (root / 'conker/conker.us.bin').read_bytes()
    elf = (root / 'conker/build/conker.us.elf').read_bytes()
    bodies = {}
    for entry, offset, count in HELPERS:
        body = list(struct.unpack_from('>%dI' % count, rom, offset))
        if entry != COLOR:
            current = list(struct.unpack_from('>%dI' % count, elf, elf_slot_offset(elf, entry, count * 4)))
            assert current == body, ('banked helper is not retail exact', hex(entry))
        bodies[entry] = body
    data = rom[0x23B9DC:0x23B9DC + 36]
    assert data == elf[elf_slot_offset(elf, fog.TABLE, 36):elf_slot_offset(elf, fog.TABLE, 36) + 36]
    return bodies, {fog.TABLE + i: value for i, value in enumerate(data)}


def code_map(bodies, renderer_words):
    result = {entry + i * 4: word for entry, body in bodies.items() for i, word in enumerate(body)}
    result.update({renderer.screen.ENTRY + i * 4: word for i, word in enumerate(renderer_words)})
    return result


def return_map():
    return {matching.ENTRY + (origin + 2) * 4: matching.ENTRY + (index + 2) * 4
        for index, (label, origin, word) in enumerate(matching.recipe_items(matching.RAW))
        if label == origin and word >> 26 == 3}


def canonical(model):
    memory, events = model.memory.copy(), list(model.events)
    for index, replacement in model.return_events.items():
        event = events[index]
        events[index] = (*event[:3], replacement)
    for address, replacement in model.return_homes.items():
        renderer.guest.put(memory, address, replacement)
    return model.r[2], memory, events, model.calls, model.accesses


def fixture(slot=0, view=0, kind=0, direct=83, amount=10.25, count=4,
        enabled=0, flags=12, page=0, w=2.0):
    memory = dispatch.fixture(slot, view, enabled=enabled, limit=1024)
    memory.update(renderer.fixture(slot, view, count=count, enabled=enabled, flags=flags, page=page))
    memory.update({renderer.STACK + i: 0xA5 for i in range(-0x1000, 0x100)})
    actor = renderer.S['D_800CC2D0'] + slot * 0x32C
    for tier in range(5):
        for selected in (0, 1):
            renderer.guest.put(memory, actor + 0x28C + tier * 8 + selected * 4, 0x27000)
    for address, value, size in ((actor + 0x74, 0, 1), (actor + 0x1D4, 0x27000, 4),
            (actor + 0x318, 0, 4), (actor + 0x1C9, 0, 1), (actor + 0xA4, kind, 1),
            (actor + 0xA0, direct if kind == 1 else 0x40802010, 4),
            (FLOAT, bits(amount), 4), (renderer.S['D_800BE9C0'], page, 1)):
        renderer.guest.put(memory, address, value, size)
    for i, value in enumerate((37, 52, 71)): memory[actor + 0xA5 + i] = value
    for i in range(6): memory[actor + 0x1DD + i] = (slot + i * 37 + 19) & 255
    for base, seed in ((PRIMITIVE, 0x31), (ENVIRONMENT, 0x93)):
        for selected_view in {0, view}:
            address = (base + selected_view * 3) & 0xFFFFFFFF
            for i in range(3): memory[address + i] = (seed + i * 29 + slot + selected_view) & 255
    shade = shading.fixture(view=view, w=w)
    memory.update({a: value for a, value in shade.items() if a >= 0x80000000})
    return memory


def colors(memory, actor, view, parameters, cosine):
    prim = tuple(memory[(PRIMITIVE + view * 3 + i) & 0xFFFFFFFF] for i in range(3))
    env = tuple(memory[(ENVIRONMENT + view * 3 + i) & 0xFFFFFFFF] for i in range(3))
    values = (0, 0, 0, parameters[3])
    if memory[actor + 0xA4]:
        # Only the reference's temporary outputs are added; real private homes
        # are compared separately by the connected instruction models.
        temporary = 0x30000
        data = memory.copy()
        for i, value in enumerate(values):
            renderer.guest.put(data, temporary + i * 4, value)
        with patch.object(fog, 'public', lambda state: state):
            data, _, _ = fog.reference(data, (actor, *(temporary + i * 4 for i in range(4))), cosine)
        values = tuple(renderer.guest.read(data, temporary + i * 4, 4) for i in range(4))
    return (*prim, *env, *values)


def reference(memory, arguments, plan=None, cosine=0.5):
    plan = plan or renderer.Plan()
    selected = renderer.Plan(plan.identity, plan.tier, plan.skip, plan.colors, plan.actions)
    live = [None]
    original_read, original_effects = renderer.guest.read, renderer.effects
    def read(state, address, size):
        live[0] = state
        return original_read(state, address, size)
    def effects(name, args):
        if name == 'func_1502CC34':
            selected.colors = colors(live[0], args[0], arguments[2], args[3], cosine)
        if name == 'func_151EFE88':
            return tuple((args[0] + i * 4, value, 4) for i, value in enumerate(IDENTITY_WORDS))
        return original_effects(name, args) if name != 'func_1502CC34' else ()
    with patch.object(renderer.guest, 'read', read), patch.object(renderer, 'effects', effects):
        return renderer.reference(memory, arguments, selected)


class ConnectedOracle(renderer.RendererOracle):
    def get(self, address, size):
        value = super().get(address, size)
        if self.return_instruction and value in self.returns:
            assert size == 4 and not renderer.public(address)
            self.return_events[len(self.events) - 1] = self.returns[value]
        return value

    def put(self, address, value, size):
        super().put(address, value, size)
        if not self.recording:
            return
        for prior in list(self.return_homes):
            if address < prior + 4 and prior < address + size:
                del self.return_homes[prior]
        if self.return_instruction and value in self.returns:
            assert size == 4 and not renderer.public(address)
            self.return_events[len(self.events) - 1] = self.returns[value]
            self.return_homes[address] = self.returns[value]

    def execute(self, word):
        self.return_instruction = word >> 26 in (35, 43) and word >> 21 & 31 == 29 and word >> 16 & 31 == 31
        try:
            if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 13:
                self.f[word >> 6 & 31] = shading.truncate(shading.floating(self.f[word >> 11 & 31]))
            else:
                super().execute(word)
        finally:
            self.return_instruction = False

    def __init__(self, words, memory, arguments, bodies, data, phase=0, plan=None,
            dispatch_plan=None, cosine=0.5, caller=False, returns=None):
        self.returns = returns or {}
        self.return_instruction = False
        self.return_events, self.return_homes = {}, {}
        connected = code_map(bodies, words)
        entry = CALLER if caller else renderer.screen.ENTRY
        renderer.guest.AttachmentOracle.__init__(self, bodies[CALLER] if caller else words, memory,
            entry=entry, arguments=arguments, phase=phase, connected=connected)
        self.plan, self.counts, self.pending = plan or renderer.Plan(), {}, None
        self.dispatch_plan = dispatch_plan or dispatch.Plan()
        self.cosine, self.render_inputs, self.color_inputs = bits(cosine), [], []
        self.memory.update(data)

    def record_call(self, target):
        if target == COLOR:
            self.color_inputs.append((self.memory.copy(), self.arguments(14)))
        if target in (renderer.S[name] for name in renderer.COUNTS):
            return renderer.RendererOracle.record_call(self, target)
        if target in (dispatch.S[name] for name in dispatch.NAMES):
            if target == renderer.screen.ENTRY:
                self.render_inputs.append((self.memory.copy(), self.arguments(8)))
            return dispatch.DispatchOracle.record_call(self, target)
        if target == fog.COS:
            event = ('CALL', 'cosf', (self.f[12],))
        else:
            assert target in INNER_COUNTS, ('unexpected connected helper', hex(target))
            event = ('CALL', 'actual-%X' % target, self.arguments(INNER_COUNTS[target]))
        self.calls.append(event)
        self.events.append(event)

    def hook(self, target):
        assert target not in ACTUAL, ('actual helper cannot be modeled', hex(target))
        if target == fog.COS:
            for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            self.f[0] = self.cosine
            return
        if target in (renderer.S[name] for name in renderer.COUNTS):
            return renderer.RendererOracle.hook(self, target)
        assert target in (dispatch.S[name] for name in dispatch.NAMES)
        saved = self.plan
        try:
            self.plan = self.dispatch_plan
            return dispatch.DispatchOracle.hook(self, target)
        finally:
            self.plan = saved
