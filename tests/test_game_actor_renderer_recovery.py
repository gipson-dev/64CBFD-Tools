"""Complete renderer recovery; public proofs do not close private layout or hardware gates."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_renderer_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

S, STACK = screen.SYMBOLS, guest.STACK
OUTPUT, CONFIG, PARAMETERS, PARTS, SPECIAL, LIGHTS = 0x20000, 0x22000, 0x23000, 0x24000, 0x25000, 0x26000
COUNTS = dict(func_150849CC=2, func_1503DA9C=4, func_1502F01C=2,
    func_1502F9FC=2, func_1502CC34=14, func_1515D914=14,
    func_151EFE88=1, func_1502FD70=1, func_15030F94=4)
COLORS = (0x123, -1, 0x345, 0x456, 0x789, -2, 0x89A, 0xABC, -3, 0xDEF)
CURSOR_CALLS = ('func_1502F01C', 'func_1502F9FC', 'func_1515D914', 'func_15030F94')


def public(address):
    return not STACK - 0x800 <= address < STACK + 0x100


def fixture(slot=0, view=0, identity=7, count=4, page=0, tier=1, flags=12,
        enabled=0, lighting=1, skip=0, override=0, matrix=True, special=True, history=0):
    memory = {STACK + i: 0xA5 for i in range(-0x800, 0x100)}
    actor = (S['D_800CC2D0'] + (slot & 0xFFFFFFFF) * 0x32C) & 0xFFFFFFFF
    for address, length in ((actor, 0x32C), (OUTPUT, 0x1800), (CONFIG, 0x80),
            (PARAMETERS, 16), (PARTS, 256), (SPECIAL, 256), (LIGHTS, 64),
            (S['D_800C3E98'], 64)):
        memory.update({address + i: (i * 17 + 53) & 255 for i in range(length)})
    for kind in (identity, 10, 255):
        for name, step, value in (('D_800C4778', 2, count), ('D_800C4488', 4, PARTS),
                ('D_800C48F0', 4, SPECIAL if special else 0)):
            guest.put(memory, S[name] + kind * step, value, step)
    for part in range(64):
        guest.put(memory, PARTS + part * 4, 0x02000000 + part * 0x100)
        guest.put(memory, SPECIAL + part * 4, 0x03000000 + part * 0x100)
    for address, value, size in ((actor + 4, identity, 1), (actor + 0x1C8, tier, 1),
            (actor + 0x66, flags, 1), (actor + 0x94, skip, 4), (actor + 0x98, override, 4),
            (actor + 0x2FE, history, 1), (actor + 0x301, 0x81, 1),
            (actor + 0x314, LIGHTS, 4), (actor + 0x184, 0x87654321, 4),
            (S['D_800BE9C0'], page, 1), (S['D_800B0DF0'], CONFIG, 4),
            (CONFIG + 0x3E, enabled, 2), (S['D_800DCD7C'], lighting, 4),
            (S['D_800D9900'], 0, 1),
            (actor + 0x28C + tier * 8 + page * 4, 0x27000 if matrix else 0, 4),
            ((actor + 0x304 + (view & 0xFFFFFFFF) * 4) & 0xFFFFFFFF, 0xFEDCBA98, 4)):
        guest.put(memory, address, value, size)
    for axis, value in enumerate((-3.75, 4.5, -0.0)):
        guest.put(memory, actor + 0x14 + axis * 4, bits(value))
    for i, value in enumerate((11, 22, 33, 144)):
        guest.put(memory, PARAMETERS + i * 4, value)
    for i, value in enumerate((0x17, 0x83, 0xE1)):
        guest.put(memory, S['D_800DD2E4'] + i, value, 1)
    return memory


class Plan:
    def __init__(self, identity=10, tier=1, skip=0, colors=COLORS, actions=None):
        self.identity, self.tier, self.skip, self.colors = identity, tier, skip, colors
        self.actions = actions or {}


def effects(name, args):
    if name in CURSOR_CALLS:
        return ((args[0], 0xA0000000 | COUNTS[name], 4), (args[0] + 4, S[name], 4))
    if name == 'func_151EFE88':
        return tuple((args[0] + i * 4, 0xB0000000 + i, 4) for i in range(16))
    return ()


class RendererOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, args, phase=0, plan=None):
        super().__init__(words, memory, entry=screen.ENTRY, arguments=args, phase=phase)
        self.plan, self.counts, self.pending = plan or Plan(), {}, None

    def record_call(self, target):
        name = next((name for name in COUNTS if S[name] == target), None)
        assert name is not None, ('unexpected renderer callback', target)
        args = self.arguments(COUNTS[name])
        ordinal = self.counts.get(name, 0)
        self.counts[name] = ordinal + 1
        self.pending = name, args, ordinal
        normalized = list(args)
        if name == 'func_150849CC': normalized[1] = 'tier-out'
        if name == 'func_1502CC34':
            normalized[3] = tuple(self.peek(args[3] + i * 4, 4) for i in range(4))
            normalized[4:] = ['color-%d' % i for i in range(10)]
        event = ('CALL', name, tuple(normalized))
        self.calls.append(event)
        self.events.append(event)

    def hook(self, target):
        name, args, ordinal = self.pending
        result = args[0] + 8 if name in CURSOR_CALLS else 0
        if name == 'func_150849CC':
            self.put(args[1], self.plan.tier, 4)
            result = self.plan.identity
        elif name == 'func_1503DA9C': result = self.plan.skip
        elif name == 'func_1502CC34':
            for address, value in zip(args[4:], self.plan.colors): self.put(address, value, 4)
        for address, value, size in effects(name, args): self.put(address, value, size)
        for address, value, size in self.plan.actions.get((name, ordinal), ()):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result & 0xFFFFFFFF


def reference(memory, args, plan=None):
    plan = plan or Plan()
    result, calls, counts = memory.copy(), [], {}
    commands, slot, view, matrix, alpha, parameters, mode, extra = args
    actor = (S['D_800CC2D0'] + (slot & 0xFFFFFFFF) * 0x32C) & 0xFFFFFFFF
    get = lambda address, size=4: guest.read(result, address & 0xFFFFFFFF, size)
    def store(address, value, size=4): guest.put(result, address & 0xFFFFFFFF, value, size)
    def call(name, values):
        ordinal = counts.get(name, 0)
        counts[name] = ordinal + 1
        calls.append(('CALL', name, tuple(v & 0xFFFFFFFF if isinstance(v, int) else v for v in values)))
        for address, value, size in effects(name, values): store(address, value, size)
        for address, value, size in plan.actions.get((name, ordinal), ()): store(address, value, size)
        return values[0] + 8 if name in CURSOR_CALLS else 0
    def emit(first, second):
        nonlocal commands
        store(commands, first)
        store(commands + 4, second)
        commands += 8
    def color(r, g, b, a):
        return (r & 255) << 24 | (g & 255) << 16 | (b & 255) << 8 | (a & 255)
    identity = get(actor + 4, 1)
    if mode in (3, 4, 5):
        call('func_150849CC', (actor, 'tier-out'))
        identity, tier = plan.identity, plan.tier
    else: tier = get(actor + 0x1C8, 1)
    call('func_1503DA9C', (actor, identity, tier, int(mode != 3)))
    if plan.skip: return commands, result, calls
    page = get(S['D_800BE9C0'], 1)
    if not get(actor + 0x28C + tier * 8 + page * 4): return commands, result, calls
    emit(0xDE000000, S['D_80084160']) if extra else emit(0xE7000000, 0)
    commands = call('func_1502F01C', (commands, slot))
    commands = call('func_1502F9FC', (commands, slot))
    emit(0xDB06000C, matrix)
    emit(0xDB060004, get(actor + 0x28C + tier * 8 + page * 4) - 0x38)
    call('func_1502CC34', (actor, view, alpha,
        tuple(get(parameters + i * 4) for i in range(4)), *('color-%d' % i for i in range(10))))
    pr, pg, pb, er, eg, eb, fr, fg, fb, fa = plan.colors
    emit(0xDB060020, S['D_800832C0'] if mode in (3, 5) else
        S['D_80082FC0'] if signed(alpha & 0xFFFFFFFF) < 255 else S['D_80083140'])
    emit(0xD9FFF9FF, 0)
    emit(0xD9FFFFFF, 0x200 if mode == 0 else 0x400)
    enabled = get(get(S['D_800B0DF0']) + 0x3E, 2)
    lighting = True
    flags = get(actor + 0x66, 1) & 12
    if flags == 12:
        emit(0xD9FFFFFF, 0x20000)
        emit(0xD9BFFFFF, 0)
    elif flags != 8 or not get(S['D_800DCD7C']):
        emit(0xD9BDFFFF, 0)
        lighting = False
    else: emit(0xD9FFFFFF, 0x420000)
    if mode == 3:
        emit(0xD9BDFFFF, 0)
        lighting = False
    if lighting:
        flags = 2 if get(actor + 0x2FE, 1) else 10
        if get(S['D_800D9900'], 1): flags |= 8
        xyz = tuple(math.trunc(floating(get(actor + offset))) for offset in (0x14, 0x18, 0x1C))
        commands = call('func_1515D914', (commands, view, *xyz, get(actor + 0x184),
            get(actor + 0x304 + view * 4), get(actor + 0x301, 1),
            get(actor + 0x314) + get(S['D_800BE9C0'], 1) * 8, actor + 0x302,
            2, actor + 0x1DD, flags, S['D_800D9E28']))
    state, part = -1, 0
    while part < get(S['D_800C4778'] + identity * 2, 2):
        assert part < 64, 'unbounded part fixture'
        mask = 1 << (part & 31)
        if not get(actor + 0x94) & mask:
            if not get(actor + 0x98) & mask:
                if state != 0:
                    emit(0xE7000000, 0)
                    state = 0
                    fog = (get(S['D_800DD2E4'] + i, 1) for i in range(3)) if enabled else (fr, fg, fb)
                    emit(0xF8000000, color(*fog, fa))
                    emit(0xFA00F200, color(pr, pg, pb, 0))
                    emit(0xFB000000, color(er, eg, eb, alpha))
            elif state != 1:
                emit(0xE7000000, 0)
                emit(0xF8000000, 255)
                emit(0xFA00F200, 0)
                emit(0xFB000000, 255)
                state = 1
            if mode == 3:
                special = get(S['D_800C48F0'] + identity * 4)
                if special: emit(0xDE000000, get(special + part * 4))
            else:
                call('func_151EFE88', (S['D_800C3E98'],))
                emit(0xDA380003, S['D_800C3E98'] - 0x80000000)
                emit(0xDE000000, get(get(S['D_800C4488'] + identity * 4) + part * 4))
        part += 1
    call('func_1502FD70', (actor,))
    store(actor + 0x2FE, 1, 1)
    if mode == 0: commands = call('func_15030F94', (commands, actor, view, 1))
    if extra: emit(0xDE000000, S['D_80084190'])
    if mode == 0: emit(0xD9FFFDFF, 0x400)
    return commands, result, calls


def projection(model):
    return model.r[2], {a: v for a, v in model.memory.items() if public(a)}, model.calls


class GameActorRendererRecoveryTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-test'
        cls.out.mkdir(exist_ok=True)
        paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.retail = list(struct.unpack_from('>532I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.mode_meta, cls.mode_raw = screen.compile_candidate(cls.root, cls.out, 'volatile-mode',
            dict(screen.candidates())['volatile-mode'])
        cls.coverage = set()

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, slot=0, view=0, mode=0, extra=0, alpha=255, phase=0, plan=None):
        args = (OUTPUT, slot, view, 0x27000, alpha, PARAMETERS, mode, extra)
        returned, result, calls = reference(memory, args, plan)
        expected = returned, {a: v for a, v in result.items() if public(a)}, calls
        models = []
        for words in (self.retail, self.raw, self.mode_raw):
            model = RendererOracle(words, memory, args, phase, plan).run()
            self.assertEqual(projection(model), expected)
            models.append(model)
        for model in models[1:]:
            self.assertEqual([e for e in model.events if e[0] == 'CALL' or public(e[1])],
                [e for e in models[0].events if e[0] == 'CALL' or public(e[1])])
        self.coverage.update(models[0].visits)
        return models

    def test_01_complete_graphics_modes_colors_and_lighting(self):
        cases = 0
        for mode, flags, enabled, light in itertools.product((-1, 0, 1, 3, 4, 5, 6), (0, 4, 8, 12), (0, -1), (0, 1)):
            slot, view = (0, 0) if cases % 2 else (25, 3)
            memory = fixture(slot, view, flags=flags, enabled=enabled, lighting=light,
                skip=0b0010, override=0b0101, history=cases % 2, page=cases % 2)
            self.compare(memory, slot, view, mode, extra=cases % 2,
                alpha=(-1, 0, 254, 255, 256, 0x80000000)[cases % 6], phase=8 if cases % 2 else 0)
            cases += 1
        self.receipt('semantic', cases=cases, complete_retail_and_two_C_forms=True,
            independent_command_words_and_callback_ABI=True, complete_public_access_order_exact=True,
            private_or_hardware_claim=False)

    def test_02_early_returns_live_masks_and_shift_boundaries(self):
        cases = 0
        for mode, skip, matrix, special, count in itertools.product((0, 3, 4, 5), (0, -1),
                (False, True), (False, True), (0, 1, 4, 33)):
            memory = fixture(count=count, skip=0xAAAAAAAA, override=0xCCCCCCCC,
                matrix=matrix, special=special)
            self.compare(memory, mode=mode, extra=1, plan=Plan(skip=skip))
            cases += 1
        for view in (-1, 32, 0x12340002):
            self.compare(fixture(view=view), view=view, mode=1)
            cases += 1
        self.receipt('gates', cases=cases, count_zero_and_wrapped_part_shift=True,
            full_width_view_and_signed_alpha=True)

    def test_03_callback_mutations_and_captured_lifetimes(self):
        cases = 0
        actor = S['D_800CC2D0']
        for name, actions in (
                ('func_1502F01C', ((actor + 0x28C + 8, 0x27800, 4), (S['D_800BE9C0'], 1, 1))),
                ('func_1502F9FC', ((actor + 0x66, 8, 1), (CONFIG + 0x3E, -1, 2))),
                ('func_1502CC34', ((actor + 0x66, 0, 1), (actor + 0x94, 2, 4))),
                ('func_1515D914', ((S['D_800C4778'] + 14, 2, 2), (actor + 0x98, 3, 4))),
                ('func_151EFE88', ((S['D_800C4778'] + 14, 2, 2), (actor + 0x94, 2, 4),
                    (actor + 0x98, 4, 4), (S['D_800C4488'] + 28, SPECIAL, 4))),
                ('func_1502FD70', ((actor + 0x2FE, 0xA9, 1),)),
                ('func_15030F94', ((actor + 0x2FE, 0xB3, 1),))):
            for phase in (0, 8):
                self.compare(fixture(), mode=0, phase=phase, plan=Plan(actions={(name, 0): actions}))
                cases += 1
        self.receipt('mutations', cases=cases, live_count_masks_tables=True,
            captured_page_enabled_and_identity=True, callbacks_bounded_opaque=True)

    def test_03b_lighting_force_flag_and_identity_boundaries(self):
        cases = 0
        for identity, history, forced, mode in itertools.product((0, 255), (0, 1), (0, 1), (0, 4)):
            memory = fixture(identity=identity, history=history)
            guest.put(memory, S['D_800D9900'], forced, 1)
            self.compare(memory, mode=mode, plan=Plan(identity=identity))
            cases += 1
        self.receipt('lighting-flags', cases=cases, all_force_flag_paths=True, first_last_identity=True)

    def test_03c_physical_frame_and_color_homes_are_not_closed(self):
        args = (OUTPUT, 0, 0, 0x27000, 255, PARAMETERS, 0, 0)
        traces, homes = [], []
        class HomesOracle(RendererOracle):
            def record_call(self, target):
                if target == S['func_1502CC34']: homes.append(list(self.arguments(14)[4:]))
                return super().record_call(target)
        models = [HomesOracle(body, fixture(), args).run() for body in (self.retail, self.raw, self.mode_raw)]
        for model in models:
            traces.append([e for e in model.events if e[0] == 'CALL' or public(e[1])])
        self.assertNotEqual(homes[0], homes[1])
        self.assertNotEqual(models[0].memory, models[1].memory)
        self.receipt('physical-gate', original_color_homes=homes[0], raw_color_homes=homes[1],
            volatile_color_homes=homes[2], complete_private_memory_differs=True,
            public_trace_equal=[traces[0] == trace for trace in traces[1:]],
            public_agreement_does_not_close_private_lifetime=True)

    def test_04_complete_compiled_negative_controls(self):
        negatives = (
            ('wrong-fog-bit', '0x400000', 'G_FOG', dict()),
            ('primitive-byte', '0xF2, 0, primitiveR', '0, 0xF2, primitiveR', dict()),
            ('alpha-inclusive', 'alpha < 255', 'alpha <= 255', dict()),
            ('signed-alpha', 'alpha < 255', '(u32)alpha < 255', dict(alpha=-1)),
            ('wrong-part-mask', 'actor + 0x94', 'actor + 0x98', dict()),
            ('wrong-display-array', 'D_800C4488[identity][part]', 'D_800C48F0[identity][part]', dict()),
            ('missing-tail', 'actor[0x2FE] = 1;', 'actor[0x2FE] = 0;', dict()),
            ('cached-count', 'part < D_800C4778[identity]', 'part < 4', dict(count=1)))
        for name, old, new, options in negatives:
            with self.subTest(name=name):
                self.assertIn(old, screen.SELECTED)
                _, words = screen.compile_candidate(self.root, self.out, name, screen.SELECTED.replace(old, new))
                memory = fixture(count=options.get('count', 4), skip=2, override=5)
                alpha = options.get('alpha', 255)
                args = (OUTPUT, 0, 0, 0x27000, alpha, PARAMETERS, 0, 0)
                expected = RendererOracle(self.retail, memory, args).run()
                damaged = RendererOracle(words, memory, args).run()
                self.assertNotEqual(projection(damaged), projection(expected))
        self.receipt('negatives', effective_complete_compiled_forms=len(negatives))

    def test_05_measured_layout_remains_an_installation_gate(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame']), (524, 0x148))
        self.assertEqual((self.mode_meta['body_words'], self.mode_meta['frame']), (533, 0x148))
        self.assertEqual(self.meta['pool_bytes'], 0)
        self.assertEqual(self.mode_meta['pool_bytes'], 0)
        before = (self.out / 'before-source').read_bytes()
        self.assertIn(screen.ORIGINAL, before.decode())
        self.assertEqual((self.root / screen.SOURCE).read_bytes(), before)
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(),
            (self.out / 'before-guards').read_bytes())
        hashes = json.loads((self.out / 'baseline.json').read_text())
        for name, path in dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
                guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
                rodata='conker/asm/data/23B8A0.rodata.s').items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), hashes[name])
        self.receipt('layout-gate', original_words=532, original_frame=0x150,
            raw=self.meta, volatile_mode=self.mode_meta, source_and_guards_unchanged=True,
            installation_not_authorized_by_public_proof=True)

    def test_06_copied_owner_neighbors_and_prototype_scope(self):
        before = (self.out / 'before-source').read_text()
        objects = []
        for name, source in (('owner-before', before), ('owner-candidate', screen.copied_owner(before))):
            obj, warnings = compile_owner(self.root, self.out, source, name)
            self.assertFalse(warnings)
            objects.append(obj)
        old_text, old_functions, old_rel = parse_object(objects[0])
        new_text, new_functions, new_rel = parse_object(objects[1])
        raw_text, raw_functions, raw_rel = parse_object(self.out / 'selected.o')
        def body(text, functions, relocations, name):
            meta = functions[name]
            start, end = meta['value'], meta['value'] + meta['size']
            return text[start:end], {offset - start: entries for offset, entries in relocations.items()
                if start <= offset < end}
        neighbors = 0
        for name in old_functions:
            if name == screen.FUNCTION: continue
            self.assertEqual(body(old_text, old_functions, old_rel, name),
                body(new_text, new_functions, new_rel, name), name)
            neighbors += 1
        self.assertEqual(body(new_text, new_functions, new_rel, screen.FUNCTION),
            body(raw_text, raw_functions, raw_rel, screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.receipt('owner', neighbors=neighbors, bodies_and_relative_relocations_exact=True,
            normalized_pools_exact=True, target_equals_isolated=True, compiler_diagnostics=0,
            copied_prototype_changes_only=True, consumer_not_installed=True)

    def test_07_independent_original_and_candidate_symbol_rebases(self):
        assembly = (self.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + screen.FUNCTION, 1)[1].split('endlabel ' + screen.FUNCTION, 1)[0]
        self.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + screen.FUNCTION +
            '\n.type ' + screen.FUNCTION + ',@function\n' + screen.FUNCTION + ':\n' + assembly +
            '\n.size ' + screen.FUNCTION + ',.-' + screen.FUNCTION + '\n')
        cases = 0
        original_symbols = dict(S)
        for delta in (0, 0x47FFC, 0x58004):
            symbols = {name: (value + (0 if name.startswith('func_') else delta)) & 0xFFFFFFFF
                for name, value in original_symbols.items()}
            script = self.out / ('rebase-%X.ld' % delta)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % screen.ENTRY)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf),
                str(self.out / 'original.o')], check=True, capture_output=True)
            original = list(struct.unpack_from('>532I', sections(elf)['.text'][1]))
            if delta == 0: self.assertEqual(original, self.retail)
            with patch.dict(S, symbols, clear=True):
                _, raw = screen.compile_candidate(self.root, self.out, 'rebase-%X' % delta)
                for mode in (0, 3, 5):
                    args = (OUTPUT, 0, 0, 0x27000, -1, PARAMETERS, mode, 1)
                    memory = fixture(skip=2, override=5)
                    returned, result, calls = reference(memory, args)
                    expected = returned, {a: v for a, v in result.items() if public(a)}, calls
                    models = [RendererOracle(body, memory, args).run() for body in (original, raw)]
                    for model in models: self.assertEqual(projection(model), expected)
                    self.assertEqual([e for e in models[0].events if e[0] == 'CALL' or public(e[1])],
                        [e for e in models[1].events if e[0] == 'CALL' or public(e[1])])
                    cases += 1
        self.receipt('rebases', independent_links=6, cases=cases, signed_LO16_carries=True,
            retained_virtual_and_physical_symbols=True, complete_public_semantics_and_order=True,
            byte_matching_or_private_layout_not_claimed=True)

    @classmethod
    def tearDownClass(cls):
        missing = [i for i in range(532) if screen.ENTRY + i * 4 not in cls.coverage]
        (cls.out / 'coverage.json').write_text(json.dumps(dict(covered=532 - len(missing),
            words=532, missing=missing, original_complete_renderer=True), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
