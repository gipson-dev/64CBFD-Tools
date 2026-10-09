"""Complete height response, conditional snapshot, six-argument ABI and guards."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout, load_section
from tools.experiments import game_record_height_response_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_graphics_dispatch_match import DispatchOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.test_game_record_phase_shaping_match import PhaseReference, signed
from tools.tests import test_game_wrapped_record_step_match as motion
from tools.tests import test_game_actor_timer_callbacks_match as timer
from tools.tests import test_game_payload_callback_update_match as dispatcher
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
ACTOR, PAYLOAD, RECORDS = motion.ACTOR, motion.PAYLOAD, motion.RECORDS
CALLBACK, ALT_CALLBACK = 0x15160000, 0x15170000


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS + '\n', '')
    assert old.count(screen.ORIGINAL) == 1
    return old, old.replace('/* Non-matching placeholders', screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)


def fixture(start=0, head=2, count=5, flags=1, selector=1, kind=3, phase=0,
        previous=(bits(3.25), bits(1.25), bits(-2.5)), symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = motion.fixture(start=head, end=start, count=count, symbols=symbols)
    for index in range(-300, 260): put(memory, RECORDS + index * 20 + 12, bits(-1.25))
    for offset, value in ((0x18, flags), (0x23, selector), (0x24, selector)):
        put(memory, PAYLOAD + offset, value, 1)
    put(memory, ACTOR + 0x2C, 2, 1); put(memory, ACTOR + 0x7D, kind, 1)
    put(memory, ACTOR + 0x60, bits(2.5))
    for i, value in enumerate(previous): put(memory, STACK + phase - 88 + 64 + i * 4, value)
    for table in ('D_8008A430', 'D_8008A450'):
        for index in range(-128, 256):
            put(memory, symbols[table] + index * 4, (CALLBACK if table.endswith('430') else ALT_CALLBACK) + (index & 3) * 0x100)
    return memory


def query_actions(memory, position, mode, symbols):
    actions = [(ACTOR + 0x60, bits(3.25), 4)]
    if mode == 1:
        actions += [(ACTOR + 0x7D, 3, 1), (PAYLOAD + 0x24, 2, 1),
            (symbols['D_8008A450'] + 8, ALT_CALLBACK + 0x400, 4), (ACTOR + 0x98, PAYLOAD + 64, 4)]
    elif mode == 2:
        actions += [(ACTOR + 0x7D, 1, 1), (PAYLOAD + 0x23, 3, 1),
            (symbols['D_8008A430'] + 12, CALLBACK + 0x400, 4), (position, bits(-9.), 4),
            (position + 4, bits(8.), 4), (position + 8, bits(7.), 4)]
    elif mode == 3:
        actions += [(PAYLOAD + 0x23, 0, 1), (PAYLOAD + 0x24, 0, 1)]
    elif mode == 5:
        actions += [(ACTOR + 0x94, RECORDS + 20, 4), (ACTOR + 0x7D, 0, 1),
            (symbols['D_8008A430'] + read(memory, PAYLOAD + 0x23, 1) * 4, CALLBACK + 0x500, 4)]
    return actions


class LoopBound(Exception):
    pass


class HeightReference(PhaseReference):
    def __init__(self, memory, query_result=1, response_result=1, mode=0, phase=0,
            bound=32, symbols=None, stack=None, actual_response=False):
        super().__init__(memory, bound)
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.stack = STACK + phase - 88 if stack is None else stack
        self.query_result, self.response_result, self.mode = query_result, response_result, mode
        self.calls, self.cursor_reads, self.actual_response = [], 0, actual_response

    def get(self, address, size=4):
        value = super().get(address, size)
        if address == ACTOR + 0x2D and size == 1:
            self.cursor_reads += 1
            if self.cursor_reads >= self.bound: raise LoopBound()
        return value

    def call(self, target, args):
        self.calls.append((target, args)); self.events.append(('CALL', target, args))

    def homes(self):
        if self.mode == 4:
            for i in range(8): self.put(self.stack + i * 4, 0x76540000 + i, 4)

    def run(self):
        payload = self.get(ACTOR + 0x98); records = self.get(ACTOR + 0x94)
        flags = self.get(payload + 24, 1); index = signed(self.get(ACTOR + 46, 1))
        if flags & 7:
            start = signed(self.get(ACTOR + 45, 1))
            for i in range(3): self.put(self.stack + 64 + i * 4, self.get(records + start * 20 + i * 4), 4)
        delta = self.symbols['D_800BE9A4']
        while True:
            index -= 1
            if index < 0: index = self.get(ACTOR + 37, 1) - 1
            record = (records + index * 20) & 0xFFFFFFFF
            gravity = self.get(payload + 16); step = self.get(delta)
            product = bits(floating(gravity) * floating(step))
            vy = self.get(record + 12); next_vy = bits(floating(vy) - floating(product))
            x = self.get(record); self.put(record + 12, next_vy, 4)
            step = self.get(delta); vx = self.get(payload + 4); vy = self.get(record + 12)
            next_x = bits(floating(x) + floating(bits(floating(vx) * floating(step))))
            y = self.get(record + 4); self.put(record, next_x, 4)
            step = self.get(delta)
            next_y = bits(floating(y) + floating(bits(floating(vy) * floating(step))))
            z = self.get(record + 8); self.put(record + 4, next_y, 4)
            step = self.get(delta); vz = self.get(payload + 12)
            self.put(record + 8, bits(floating(z) + floating(bits(floating(vz) * floating(step)))), 4)
            end = signed(self.get(ACTOR + 45, 1))
            if index == end: break
        flags = self.get(payload + 24, 1)
        if flags & 0x17:
            old_y = self.get(self.stack + 68); record = records + end * 20
            y = self.get(record + 4)
            if floating(y) < floating(old_y):
                x = self.get(record); self.put(self.stack + 56, old_y, 4)
                self.put(self.stack + 52, x, 4)
                start = signed(self.get(ACTOR + 45, 1))
                self.put(self.stack + 60, self.get(records + start * 20 + 8), 4)
                start = signed(self.get(ACTOR + 45, 1)); height = self.get(records + start * 20 + 4)
                self.put(self.stack + 80, payload, 4)
                position = self.stack + 52
                self.call(self.symbols['func_15046C80'], (position, 0, height, ACTOR + 96))
                for i in range(3): self.get(position + i * 4)
                for address, value, size in query_actions(self.memory, position, self.mode, self.symbols):
                    self.put(address, value, size)
                self.homes(); payload = self.get(self.stack + 80)
                if self.query_result:
                    kind = self.get(ACTOR + 125, 1)
                    selector = self.get(payload + (36 if kind == 3 else 35), 1)
                    old_x = self.get(self.stack + 64); old_y = self.get(self.stack + 68)
                    if selector:
                        table = self.symbols['D_8008A450' if kind == 3 else 'D_8008A430']
                        target = self.get(table + selector * 4); height = self.get(ACTOR + 96)
                        self.put(self.stack + 20, ACTOR + 100, 4)
                        old_z = self.get(self.stack + 72); self.put(self.stack + 16, height, 4)
                        args = (ACTOR, old_x, old_y, old_z, self.get(self.stack + 16), self.get(self.stack + 20))
                        self.call(target, args)
                        if self.actual_response:
                            self.put(payload + 32, 4, 1)
                        else:
                            self.put(ACTOR + 108, 0xCCCC0000 | (target & 65535), 4); self.homes()
                        self.returned = int(bool(self.response_result)); return self
        self.returned = 1
        return self


class HeightOracle(DispatchOracle):
    def __init__(self, words, memory, query_result=1, response_result=1, mode=0, phase=0,
            entry=screen.ENTRY, bound=32, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry, connected=connected)
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.query_result, self.response_result, self.mode = query_result, response_result, mode
        self.bound, self.cursor_reads = bound, 0

    def get(self, address, size):
        value = super().get(address, size)
        if address == ACTOR + 45 and size == 1:
            self.cursor_reads += 1
            if self.cursor_reads >= self.bound: raise LoopBound()
        return value

    def put(self, address, value, size):
        if self.recording:
            assert address % size == 0, ('unaligned store', address, size)
            assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        if target in (dispatcher.screen.ENTRY, screen.ENTRY):
            self.calls.append((target, self.arguments(1)))
            return
        args = self.arguments(4 if target == self.symbols['func_15046C80'] else 6)
        self.calls.append((target, args)); self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == self.symbols['func_15046C80']:
            position = self.r[4]
            for i in range(3): self.get(position + i * 4, 4)
            for address, value, size in query_actions(self.memory, position, self.mode, self.symbols):
                self.put(address, value, size)
            result = self.query_result
        else:
            self.put(ACTOR + 108, 0xCCCC0000 | (target & 65535), 4)
            result = self.response_result
        if self.mode == 4:
            for i in range(8): self.put(self.r[29] + i * 4, 0x76540000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result & 0xFFFFFFFF


def state(model):
    try:
        model.run(); return 'returned'
    except LoopBound:
        return 'bounded-prefix'
    except AssertionError as error:
        assert isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return 'fault'


class GameRecordHeightResponseMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-height-response-test'; cls.out.mkdir(exist_ok=True)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>143I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup); cls.path = Path(cls.directory.name)
        if not (cls.out / 'baseline.json').exists():
            old, _ = shapes(cls.root); assert (cls.root / SOURCE).read_text() == old
            slots, _ = timer.slot_records(cls.root)
            prior = json.loads((cls.root / 'conker/build/game-record-growth-test/after.json').read_text())
            assert slots == prior['slots'] and len(slots) == 6058
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes(); (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())
            (cls.out / 'baseline.json').write_text(json.dumps(dict(slots=slots,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, query_result=1, response_result=1, mode=0, phase=0, bound=32,
            words=None, entry=screen.ENTRY, symbols=None, raw=True):
        ref = HeightReference(memory, query_result, response_result, mode, phase, bound, symbols)
        expected = state(ref); models = []
        bodies = (self.words, self.retail, self.raw) if raw else (self.words, self.retail)
        for body in ((words,) if words is not None else bodies):
            model = HeightOracle(body, memory, query_result, response_result, mode, phase, entry, bound, symbols)
            self.assertEqual(state(model), expected)
            self.assertEqual((external(model.memory), public(model.events), model.calls, model.cursor_reads),
                (external(ref.memory), public(ref.events), ref.calls, ref.cursor_reads))
            if expected == 'returned': self.assertEqual(model.r[2], ref.returned)
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events, models[0].calls),
                (models[1].r, models[1].f, models[1].memory, models[1].events, models[1].calls))
            if raw:
                self.assertEqual((models[2].r, models[2].f), (models[0].r, models[0].f))
                differing = {a for a in models[2].memory if models[2].memory[a] != models[0].memory[a]}
                self.assertLessEqual(differing, {STACK + phase - 88 + o for o in (*range(80, 84), *range(84, 88))})
        return expected, models

    def test_01_complete_slot_three_closed_guards_and_stale_rejection(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (143, 88, 3))
        self.assertEqual(self.words, self.retail); self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual({i for i, (a, b) in enumerate(zip(self.raw, self.words)) if a != b}, {18, 92, 94})
        for index, _, _ in screen.PATCHES:
            stale = list(self.raw); stale[index] ^= 1
            with self.assertRaises(AssertionError): screen.normalize(stale)
        control = list(self.raw); control[1] ^= 1; self.assertEqual(screen.normalize(control)[1], control[1])
        self.assertEqual(dict(self.meta['relocations']), {20: [('R_MIPS_HI16', 'D_800BE9A4')],
            36: [('R_MIPS_LO16', 'D_800BE9A4')], 364: [('R_MIPS_26', 'func_15046C80')],
            420: [('R_MIPS_HI16', 'D_8008A450')], 428: [('R_MIPS_LO16', 'D_8008A450')],
            496: [('R_MIPS_HI16', 'D_8008A430')], 504: [('R_MIPS_LO16', 'D_8008A430')]})
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=143, bytes=572, frame=88, guards=3, profiles=profiles,
            closed_payload_carry='SP+0x54 -> SP+0x50; store/load only', direct_matching=False))

    def test_02_metadata_selectors_results_mutations_and_complete_coverage(self):
        visited, count, bounded = set(), 0, 0
        for field, value, phase in itertools.product(('start', 'head', 'count', 'flags', 'kind'), range(256), (0, 8)):
            result, models = self.compare(fixture(**{field: value, 'phase': phase}), phase=phase, bound=16)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        for selector, response, kind in itertools.product(range(256), (0, 1, 0x80000000), (1, 3)):
            result, models = self.compare(fixture(selector=selector, kind=kind), response_result=response)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        for mode, query, response, kind, phase in itertools.product(range(6), (0, 1), (0, 0x80000000), (1, 3), (0, 8)):
            result, models = self.compare(fixture(kind=kind, phase=phase), query, response, mode, phase)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        for delta in (0, 0x7FC00001):
            memory = fixture(); put(memory, screen.SYMBOLS['D_800BE9A4'], delta)
            result, models = self.compare(memory)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        missing = sorted((a - screen.ENTRY) // 4 for a in set(range(screen.ENTRY, screen.ENTRY + 572, 4)) - visited)
        self.assertEqual(missing, [118])
        self.receipt('guest', dict(cases=count, executions=count * 3, bounded_prefixes=bounded,
            reachable_words=len(visited), unreachable_word_indices=missing, live_query_mutations_and_home_clobbers=True,
            all_byte_cursors_count_flags_kind_and_both_selectors=True, negative_return_normalizes_to_one=True))

    def test_03_conditional_snapshot_float_edges_and_private_carry_lifetime(self):
        count = 0
        for flags, prior_y, phase, kind in itertools.product((0, 1, 7, 16, 17, 32),
                (0, 0x80000000, bits(1.25), bits(-1.25), 0x7F800000, 0x7FC00001), (0, 8), (1, 3)):
            memory = fixture(flags=flags, phase=phase, kind=kind, previous=(bits(3.25), prior_y, bits(-2.5)))
            _, models = self.compare(memory, phase=phase); count += 1
            snapshot_writes = [e for e in models[0].events if e[0] == 'W' and e[1] == STACK + phase - 88 + 64]
            self.assertEqual(bool(snapshot_writes), bool(flags & 7))
        self.receipt('snapshot', dict(cases=count, executions=count * 3, prior_stack_float_patterns=True,
            bit16_only_read_is_emitted_not_portable_C=True, zero_default_not_invented=True,
            carry_slots_50_and_54_are_outside_snapshot_40_to_4B_query_34_to_3F_and_homes_00_to_1F=True))

    def test_04_lazy_gates_fault_prefixes_and_live_public_aliases(self):
        count = 0
        for kwargs, query, mode in (({}, 1, 0), (dict(flags=0), 1, 0), (dict(selector=0), 1, 0),
                (dict(flags=16), 0, 4), (dict(kind=1), 1, 2)):
            memory = fixture(**kwargs); _, models = self.compare(memory, query_result=query, mode=mode)
            touched = {event[1] + i for event in public(models[0].events) if event[0] != 'CALL' for i in range(event[2])}
            for address in sorted(touched):
                missing = dict(memory); del missing[address]
                self.compare(missing, query_result=query, mode=mode); count += 1
        aliases = 0
        for location, flags, phase in itertools.product((ACTOR + 0x10, ACTOR + 0x24,
                ACTOR + 0x2C, ACTOR + 0x94, ACTOR + 0x98, PAYLOAD + 0x18), (0, 1, 16), (0, 8)):
            memory = fixture(head=1, flags=flags, phase=phase); put(memory, ACTOR + 0x94, location - 12)
            self.compare(memory, phase=phase, bound=12); aliases += 1
        memory = fixture(head=1, flags=0)
        time = screen.SYMBOLS['D_800BE9A4']
        for i in range(-16, 24): memory[time + i] = 0
        for i, value in enumerate((2., 3., 4., -1.)): put(memory, time - 12 + i * 4, bits(value))
        put(memory, ACTOR + 0x94, time - 12); self.compare(memory); aliases += 1
        self.receipt('faults-aliases', dict(missing_public_byte_triples=count, aliases=aliases, alias_executions=aliases * 3,
            emitted_fault_and_public_alias_order_not_portable_C_or_private_stack_alias_claims=True))

    def test_05_effective_compiled_semantic_negatives(self):
        negatives = {
            'unsigned-start': screen.SELECTED.replace('*(s8 *)(actor + 0x2D)', 'actor[0x2D]'),
            'unsigned-head': screen.SELECTED.replace('*(s8 *)(actor + 0x2E)', 'actor[0x2E]'),
            'signed-count': screen.SELECTED.replace('actor[0x25]', '*(s8 *)(actor + 0x25)'),
            'expanded-snapshot-gate': screen.SELECTED.replace('payload[0x18] & 7', 'payload[0x18] & 0x17'),
            'wrong-response-mask': screen.SELECTED.replace('payload[0x18] & 0x17', 'payload[0x18] & 7'),
            'wrong-kind': screen.SELECTED.replace('actor[0x7D] == 3', 'actor[0x7D] == 1'),
            'wrong-callback-height': screen.SELECTED.replace('*(f32 *)(actor + 0x60)', 'previous.y'),
            'negative-result-fails': screen.SELECTED.replace('actor + 0x64) == 0)', 'actor + 0x64) <= 0)'),
        }
        samples = [(fixture(**kwargs), query, response, mode) for kwargs, query, response, mode in (
            ({}, 1, 0, 0), ({'kind': 1}, 1, 0x80000000, 1), ({'flags': 16}, 1, 1, 0),
            ({'start': 255}, 0, 1, 0), ({'head': 128, 'count': 255}, 0, 1, 0),
            ({'start': 127, 'head': 0, 'count': 128}, 0, 1, 0), ({'kind': 3}, 1, 1, 2))]
        samples.append((fixture(start=255, head=0, count=0), 0, 1, 0))
        records = []
        for name, body in negatives.items():
            meta, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            changed = 0
            for memory, query, response, mode in samples:
                ref = HeightReference(memory, query, response, mode, bound=12)
                model = HeightOracle(words, memory, query, response, mode, bound=12)
                expected, observed = state(ref), state(model)
                changed += (expected, external(ref.memory), ref.calls, ref.returned) != (
                    observed, external(model.memory), model.calls, model.r[2] if observed == 'returned' else None)
            self.assertGreater(changed, 0, name); records.append(dict(meta, semantic_differences=changed))
        self.receipt('negatives', dict(effective_negatives=len(records), samples=len(samples), records=records))

    def test_06_owner_postprocessing_neighbors_actual_padding_and_rebased_symbols(self):
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, warning = compile_owner(self.root, self.out, text, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj); warnings.append(warning)
        self.assertEqual(warnings, [[], []])
        old, before, old_rel = parse_object(objects[0]); text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION: continue
            prev = before[name]
            self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']]), name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prev['value']: r for o, r in old_rel.items() if prev['value'] <= o < prev['value'] + prev['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream: rows = list(csv.DictReader(stream))
        guard_file = self.out / 'candidate-guards.csv'
        with guard_file.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows + screen.guard_rows())
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=guard_file, filename='generated_175250')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('\n', assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)) + 1
        self.assertNotIn('.space', assembly[start:end]); asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 572)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations']); count = 0
        for variant, (entry, time, query, low) in enumerate(((screen.ENTRY, 0x800BE9A4, 0x15046C80, 0x8008A430),
                (0x10007FFC, 0x80007FFC, 0x10004C80, 0x80007FF0), (0x80008000, 0x80008000, 0x80004C80, 0x80008010),
                (0x8FFF7FFC, 0x8000FFF0, 0x8FFF4C80, 0x8000FFF8))):
            symbols = dict(D_800BE9A4=time, func_15046C80=query, D_8008A430=low,
                D_8008A450=low + (0x20 if not variant else 0x800))
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>143I', sections(elf)['.text'][1]))
            if not variant: self.assertEqual(words, self.retail)
            for flags, kind, query_result, phase in itertools.product((0, 1, 16), (1, 3), (0, 1), (0, 8)):
                self.compare(fixture(flags=flags, kind=kind, phase=phase, symbols=symbols), query_result=query_result,
                    phase=phase, words=words, entry=entry, symbols=symbols); count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0, guards=3, padding_bytes=572,
            pools_and_relative_relocations_unchanged=True, independent_links=4, cases=count))

    def test_07_whole_ELF_identical_guards_append_and_one_conversion_row(self):
        baseline = json.loads((self.out / 'baseline.json').read_text()); old, new = shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == new; slots, functions = timer.slot_records(self.root)
        self.assertEqual(slots, baseline['slots']); self.assertEqual(functions[screen.FUNCTION], self.retail)
        elf = self.root / 'conker/build/conker.us.elf'; self.assertEqual(elf.read_bytes(), (self.out / 'before.elf').read_bytes())
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        with (self.out / 'before-progress.csv').open(newline='') as stream: progress = list(csv.DictReader(stream))
        with (self.root / 'conker/progress.csv').open(newline='') as stream: after = list(csv.DictReader(stream))
        self.assertEqual(after, [dict(row, language='c') if installed and row['function'] == screen.FUNCTION else row for row in progress])
        before = (self.out / 'before-retail_word_patches.us.csv').read_bytes()
        self.assertTrue((self.root / 'conker/retail_word_patches.us.csv').read_bytes().startswith(before))
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream: guards = list(csv.DictReader(stream))
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream: old_guards = list(csv.DictReader(stream))
        self.assertEqual(guards, old_guards + (screen.guard_rows() if installed else []))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), full_ELF_byte_identical=True,
            guards=len(guards), old_guard_bytes_preserved=True, conversion_changes=1 if installed else 0,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed: self.receipt('after', dict(slots=slots, guards=guards, progress=after))

    def test_08_actual_native32_defined_pairs_six_arguments_and_full_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct {f32 x,y,z,velocityY,reserved;} MotionRecord15148AF4;
''' + screen.DECLARATIONS + r'''
static union {u32 align;u8 b[256];} actor,wantedActor;
static union {u32 align;u8 b[128];} payload,wantedPayload;
static MotionRecord15148AF4 records[560],wanted[560];
static RecordPosition15148BA4 expectedPrevious,expectedQuery;
static f32 expectedHeight;static int queryResult,responseResult,newKind,expectedCalls,calls,error,expectedTable;
f32 D_800BE9A4;
static u32 word(f32 x) {union {f32 f;u32 u;} q;q.f=x;return q.u;}
static s32 respond(int table,u8 *p,f32 x,f32 y,f32 z,f32 height,void *result) {
    calls++;if(p!=actor.b || table!=expectedTable || word(x)!=word(expectedPrevious.x)
        || word(y)!=word(expectedPrevious.y) || word(z)!=word(expectedPrevious.z)
        || word(height)!=word(3.25f) || result!=actor.b+100) error=1;
    *(u32 *)(actor.b+108)=0xCCCC0000;return responseResult;
}
static s32 normal(u8 *p,f32 x,f32 y,f32 z,f32 h,void *r) {return respond(0,p,x,y,z,h,r);}
static s32 special(u8 *p,f32 x,f32 y,f32 z,f32 h,void *r) {return respond(1,p,x,y,z,h,r);}
s32 (*D_8008A430[256])(u8 *,f32,f32,f32,f32,void *);
s32 (*D_8008A450[256])(u8 *,f32,f32,f32,f32,void *);
s32 func_15046C80(f32 *p,u16 selector,f32 height,HeightResult71820 *result) {
    calls++;if(selector || result!=(HeightResult71820 *)(actor.b+96)
        || word(p[0])!=word(expectedQuery.x) || word(p[1])!=word(expectedQuery.y)
        || word(p[2])!=word(expectedQuery.z) || word(height)!=word(expectedHeight)) error=2;
    result->height=3.25f;result->state=(u8)newKind;return queryResult;
}
static int expected(int flags,int selector) {
    int index=(s8)wantedActor.b[46],end=(s8)wantedActor.b[45],count=wantedActor.b[37];
    MotionRecord15148AF4 *p;volatile f32 product;
    expectedCalls=0;
    if(flags&7) expectedPrevious=*(RecordPosition15148BA4 *)(wanted+300+end);
    do {
        if(--index<0) {index=count-1;} p=wanted+300+index;
        product=*(f32 *)(payload.b+16)*D_800BE9A4;p->velocityY-=product;
        product=*(f32 *)(payload.b+4)*D_800BE9A4;p->x+=product;
        product=p->velocityY*D_800BE9A4;p->y+=product;
        product=*(f32 *)(payload.b+12)*D_800BE9A4;p->z+=product;
    } while(index!=end);
    p=wanted+300+end;
    if((flags&0x17) && p->y<expectedPrevious.y) {
        expectedQuery.x=p->x;expectedQuery.y=expectedPrevious.y;expectedQuery.z=p->z;expectedHeight=p->y;
        expectedCalls++;*(f32 *)(wantedActor.b+96)=3.25f;wantedActor.b[125]=(u8)newKind;
        if(queryResult && selector) {
            expectedCalls++;expectedTable=(newKind==3);
            *(u32 *)(wantedActor.b+108)=0xCCCC0000;return responseResult!=0;
        }
    }
    return 1;
}
'''
        self.fixture += '\n#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wmaybe-uninitialized"\n'
        self.fixture += screen.SELECTED + '\n#pragma GCC diagnostic pop\n' + r'''
static int check(int head,int count,int flags,int selector,int kind,int query,int response) {
    int i,index=(s8)head-1,result;
    if(index<0) index=count-1;
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<128;i++) payload.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<560;i++) {records[i].x=i/8.0f;records[i].y=-i/4.0f;
        records[i].z=i/16.0f;records[i].velocityY=-1.25f;records[i].reserved=123.5f;}
    *(MotionRecord15148AF4 **)(actor.b+148)=records+300;*(u8 **)(actor.b+152)=payload.b;
    actor.b[45]=(u8)index;actor.b[46]=(u8)head;actor.b[37]=(u8)count;
    actor.b[125]=(u8)(kind==3?1:3);*(f32 *)(actor.b+96)=2.5f;
    payload.b[24]=(u8)flags;payload.b[35]=(u8)selector;payload.b[36]=(u8)selector;
    *(f32 *)(payload.b+4)=0.75f;*(f32 *)(payload.b+12)=-0.25f;*(f32 *)(payload.b+16)=0.125f;
    queryResult=query;responseResult=response;newKind=kind;calls=error=0;
    D_800BE9A4=0.50000006f;wantedActor=actor;wantedPayload=payload;
    for(i=0;i<(int)sizeof(records);i++) ((u8 *)wanted)[i]=((u8 *)records)[i];
    result=expected(flags,selector);
    if(func_15148BA4(actor.b)!=result || calls!=expectedCalls || error) return 1;
    for(i=0;i<256;i++) if(actor.b[i]!=wantedActor.b[i]) return 2;
    for(i=0;i<128;i++) if(payload.b[i]!=wantedPayload.b[i]) return 3;
    for(i=0;i<(int)sizeof(records);i++) if(((u8 *)records)[i]!=((u8 *)wanted)[i]) return 4;
    return 0;
}
'''
        self.run_host(r'''
int head,count,selector,kind,response,i;
for(i=0;i<256;i++) {D_8008A430[i]=normal;D_8008A450[i]=special;}
for(head=0;head<256;head++) for(count=0;count<256;count++) {
    if(count>128 && (s8)head<=0) continue;
    if(check(head,count,(head+count)&1,1,((head+count)&2)?3:1,1,1)) return 1;
}
for(selector=0;selector<256;selector++) for(kind=0;kind<2;kind++) for(response=0;response<3;response++)
    if(check(2,5,1,selector,kind?3:1,1,response==0?0:response==1?1:(s32)0x80000000)) return 2;
''')
        self.receipt('native', dict(cases=50689, head_count_pairs=49153, selector_kind_result_cases=1536,
            actual_native32=True, canary_bytes=dict(actor=256, payload=128, records=11200),
            flags16_only_uninitialized_snapshot_and_cyclic_pairs_excluded=True,
            actual_query_and_six_argument_table_calls_live_kind_height_and_negative_returns=True))

    def test_09_actual_connected_timer_dispatch_and_response_body(self):
        elf = self.root / 'conker/build/conker.us.elf'; base, data = load_section(elf, '.game_data')
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A3EC - base)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A204 - base)[0], dispatcher.screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A434 - base)[0], 0x15148EF8)
        _, functions = timer.slot_records(self.root)
        outer, middle, response = (functions[n] for n in (timer.screen.FUNCTION, dispatcher.screen.FUNCTION, 'func_15148EF8'))
        self.assertEqual((len(outer), len(middle)), (100, 97)); count = 0
        for flags, query, phase in itertools.product((0, 1, 16, 17), (0, 1), (0, 8)):
            memory = fixture(flags=flags, kind=1, phase=phase)
            for offset, value, size in ((0x1E, 0, 2), (0x2F, 1, 1), (0x30, 0, 1), (0x24, 255, 1)):
                put(memory, ACTOR + offset, value, size)
            for offset, value in ((0x20, 3), (0x21, 0), (0x22, 0)): put(memory, PAYLOAD + offset, value, 1)
            put(memory, 0x8008A204, dispatcher.screen.ENTRY); put(memory, 0x8008A3EC, screen.ENTRY)
            put(memory, 0x8008A434, 0x15148EF8)
            ref = HeightReference(memory, query_result=query, phase=phase, stack=STACK + phase - 168, actual_response=True)
            self.assertEqual(state(ref), 'returned')
            for i in range(3): put(ref.memory, ACTOR + 84 + i * 4, read(ref.memory, RECORDS + i * 4))
            models = []
            for leaf in (self.words, self.retail, self.raw):
                connected = {dispatcher.screen.ENTRY + i * 4: w for i, w in enumerate(middle)}
                connected.update({screen.ENTRY + i * 4: w for i, w in enumerate(leaf)})
                connected.update({0x15148EF8 + i * 4: w for i, w in enumerate(response)})
                model = HeightOracle(outer, memory, query_result=query, phase=phase,
                    entry=timer.screen.ENTRY, connected=connected).run()
                self.assertEqual(model.calls, [(dispatcher.screen.ENTRY, (ACTOR,)), (screen.ENTRY, (ACTOR,)), *ref.calls])
                self.assertEqual(external(model.memory), external(ref.memory)); models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].events, models[1].memory)); count += 1
        self.receipt('connected', dict(cases=count, executions=count * 3, complete_words=[100, 97, 143, len(response)],
            actual_tables=['0x8008A204', '0x8008A3EC', '0x8008A434'], actual_response_body=True,
            height_hardware_query_still_bounded_stub=True, failure_cleanup_and_other_response_bodies_open=True))


if __name__ == '__main__':
    unittest.main()
