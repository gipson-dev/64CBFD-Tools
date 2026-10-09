"""Complete three-stage timer callbacks and six guarded private spill accesses."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout, load_section
from tools.experiments import game_actor_timer_callbacks_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests import test_game_actor_graphics_dispatch_match as prior
from tools.tests import test_game_trail_effect_constructor_recovery as layout
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_174BF0.c'
ACTOR, CALLBACK = 0x20000, 0x15001000
TABLES = ('D_8008A200', 'D_8008A23C', 'D_8008A284')
BOUNDS = (15, 18, 8)
WIDTHS = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0x10000, 0xFFFF0001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.INSERT, '')
    assert old.count(screen.ORIGINAL) == 1
    new = old.replace('/* Non-matching placeholders', screen.INSERT + '/* Non-matching placeholders', 1).replace(
        screen.ORIGINAL, screen.SELECTED)
    return old, new


def signed(value, width):
    value &= (1 << width) - 1
    return value if value < 1 << (width - 1) else value - (1 << width)


def fixture(selectors=(1, 1, 0), flags=0x10, timer=1, tick=1, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    memory.update({ACTOR + i: (i * 17 + 0xA5) & 255 for i in range(-16, 0x100)})
    put(memory, ACTOR + 0x1C, timer, 2)
    put(memory, ACTOR + 0x1E, flags, 2)
    for offset, selector in zip((0x2F, 0x30, 0x24), selectors):
        put(memory, ACTOR + offset, selector, 1)
    put(memory, symbols['D_800BE9E4'], tick)
    for stage, name in enumerate(TABLES):
        for i in range(BOUNDS[stage]):
            put(memory, symbols[name] + i * 4, CALLBACK + stage * 0x1000 + (i & 31) * 4)
    return memory


def actions(stage, mode, symbols):
    if stage == 0:
        return {0: (), 1: ((ACTOR + 0x30, 17, 1),), 2: ((ACTOR + 0x30, 18, 1),),
            3: ((ACTOR + 0x1E, 0, 2),), 4: ((ACTOR + 0x1E, 0x10, 2), (ACTOR + 0x24, 0xFF, 1)),
            5: ((ACTOR + 0x1E, 0x10, 2), (ACTOR + 0x24, 8, 1)),
            6: ((symbols['D_8008A23C'] + 4, CALLBACK + 0x1000 + 7 * 4, 4),), 7: ()}[mode]
    if stage == 1:
        return {0: (), 1: ((ACTOR + 0x24, 7, 1),), 2: ((ACTOR + 0x24, 0xFE, 1),),
            3: ((ACTOR + 0x1E, 0x10, 2),), 4: ((ACTOR + 0x24, 0xFF, 1),),
            5: ((ACTOR + 0x1E, 0, 2),),
            6: ((symbols['D_8008A284'], CALLBACK + 0x2000 + 7 * 4, 4),), 7: ()}[mode]
    return ()


def reference(memory, results=(1, 1, 1), mode=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory, calls = dict(memory), []
    expired = False
    if read(memory, ACTOR + 0x1E, 2) & 1:
        timer = (signed(read(memory, ACTOR + 0x1C, 2), 16) - read(memory, symbols['D_800BE9E4'])) & 65535
        put(memory, ACTOR + 0x1C, timer, 2)
        expired = bool(timer & 0x8000)
    for stage, offset in enumerate((0x2F, 0x30, 0x24)):
        if stage == 2 and not read(memory, ACTOR + 0x1E, 2) & 0x10:
            break
        selector = read(memory, ACTOR + offset, 1)
        if stage == 2:
            selector = signed(selector, 8)
        if selector >= BOUNDS[stage] or stage == 2 and selector < -1:
            calls.append(('cleanup', ACTOR))
            put(memory, ACTOR + 0x50, 0xDDDDDDDD)
            return memory, calls
        if selector != (0 if stage < 2 else -1) and not expired:
            target = read(memory, symbols[TABLES[stage]] + selector * 4)
            calls.append(('callback', stage, target, ACTOR))
            put(memory, ACTOR + 0x50, 0xCC000000 + stage)
            for address, value, size in actions(stage, mode, symbols):
                put(memory, address, value, size)
            expired = not results[stage]
    if expired:
        calls.append(('cleanup', ACTOR))
        put(memory, ACTOR + 0x50, 0xDDDDDDDD)
    return memory, calls


class TimerOracle(prior.DispatchOracle):
    def __init__(self, words, memory, results=(1, 1, 1), mode=0, phase=0, entry=screen.ENTRY, symbols=None, roles=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry)
        self.results, self.mode = results, mode
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.roles = {CALLBACK + stage * 0x1000 + i * 4: stage for stage in range(3) for i in range(32)} if roles is None else roles

    def record_call(self, target):
        actor, = self.arguments(1)
        if target == self.symbols['func_1516972C']:
            self.calls.append(('cleanup', actor))
        else:
            self.calls.append(('callback', self.roles[target], target, actor))

    def hook(self, target):
        call = self.calls[-1]
        if call[0] == 'cleanup':
            self.put(call[1] + 0x50, 0xDDDDDDDD, 4)
            result = 0xBEEF1234
        else:
            stage, actor = call[1], call[3]
            self.put(actor + 0x50, 0xCC000000 + stage, 4)
            for address, value, size in actions(stage, self.mode, self.symbols):
                self.put(address, value, size)
            if self.mode == 7:
                for i in range(4):
                    self.put(self.r[29] + i * 4, 0x76540000 + i, 4)
            result = self.results[stage]
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


def size_offset(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    offsets = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == screen.FUNCTION:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                offsets.append(offset + 8)
    assert len(offsets) == 1
    return offsets[0]


def symbol_records(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    result = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            name = names[symbol[0]:].split(b'\0', 1)[0].decode()
            result.append((name, symbol, offset, strings[4] + symbol[0]))
    return result


def exchange_absolute_symbol_order(data):
    records = symbol_records(data)
    pairs = [next(r for r in records if r[0] == name) for name in ('D_8008A200', 'D_80089800')]
    first, second = pairs
    assert first[1][1:] == (0x8008A200, 0, 16, 0, 0xFFF1)
    assert second[1][1:] == (0x80089800, 0, 16, 0, 0xFFF1)
    assert second[2] - first[2] == 16 and second[3] - first[3] == 11
    assert data[first[3]:first[3] + 11] == b'D_8008A200\0'
    assert data[second[3]:second[3] + 11] == b'D_80089800\0'
    struct.pack_into('>I', data, first[2] + 4, second[1][1])
    struct.pack_into('>I', data, second[2] + 4, first[1][1])
    data[first[3]:first[3] + 11] = b'D_80089800\0'
    data[second[3]:second[3] + 11] = b'D_8008A200\0'
    return [first[0], second[0]]


def slot_records(root):
    functions, _, addresses = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    return {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
        struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}, functions


class GameActorTimerCallbacksMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-timer-callbacks-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>100I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            before = json.loads((cls.root / 'conker/build/game-actor-graphics-dispatch-test/after.json').read_text())
            slots, _ = slot_records(cls.root)
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert (slots, guards, progress) == (before['slots'], before['guards'], before['progress'])
            assert len(slots) == 6058 and len(guards) == 11475
            old, _ = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes()
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, results=(1, 1, 1), mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None, roles=None):
        wanted, calls = reference(memory, results, mode, symbols)
        models = []
        for body in ((words,) if words is not None else (self.raw, self.words, self.retail)):
            model = TimerOracle(body, memory, results, mode, phase, entry, symbols, roles).run()
            self.assertEqual((model.calls, external(model.memory)), (calls, external(wanted)))
            models.append(model)
        if words is None:
            self.assertEqual((models[1].r, models[1].f, models[1].events, models[1].memory),
                (models[2].r, models[2].f, models[2].events, models[2].memory))
            self.assertEqual((models[0].r, models[0].f, public(models[0].events)),
                (models[2].r, models[2].f, public(models[2].events)))
        return models

    def test_01_complete_slot_six_closed_guards_profiles_and_stale_rejection(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (100, 32, 6))
        self.assertEqual((self.words, self.meta['diagnostics'], self.meta['pool_bytes']), (self.retail, '', 0))
        self.assertEqual([i for i, (a, b) in enumerate(zip(self.raw, self.words)) if a != b], [p[0] for p in screen.PATCHES])
        for i, _, _ in screen.PATCHES:
            stale = self.raw.copy()
            stale[i] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        stale = self.raw.copy()
        stale[16] ^= 1
        self.assertNotEqual(screen.normalize(stale), self.retail)
        self.assertTrue(all((a ^ b) == 4 for _, a, b in screen.PATCHES))
        self.assertTrue(all(self.raw[i] == self.words[i] for i in range(100) if i not in {p[0] for p in screen.PATCHES}))
        private_offsets = lambda words: {w & 65535 for w in words if w >> 26 in (32, 35, 40, 43) and (w >> 21 & 31) == 29}
        self.assertEqual(private_offsets(self.raw), {0x14, 0x20, 0x1F})
        self.assertEqual(private_offsets(self.words), {0x14, 0x20, 0x1B})
        relocs = [r for items in self.meta['relocations'].values() for r in items]
        self.assertEqual({symbol for _, symbol in relocs}, set(screen.SYMBOLS))
        self.assertEqual([sum(k == kind for k, _ in relocs) for kind in ('R_MIPS_26', 'R_MIPS_HI16', 'R_MIPS_LO16')], [4, 4, 4])
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=100, bytes=400, frame=32, raw_differences=6, normalized_differences=0,
            guards=screen.guard_rows(), profiles=profiles, private_spill_31_to_27_only=True))

    def test_02_stage_boundaries_timer_wrap_full_results_and_live_mutations(self):
        count, reached = 0, set()
        for stage, byte, results, phase in itertools.product(range(3), range(256),
                ((1, 1, 1), (0, 1, 1), (0x80000000, 0xFFFFFFFF, 0), (1, 0, 1)), (0, 8)):
            selectors = [1, 1, 0]
            selectors[stage] = byte
            models = self.compare(fixture(selectors=selectors), results, phase=phase)
            reached.update(models[2].visits)
            count += 1
        for flags, timer, tick, mask, phase in itertools.product((0, 1, 0x10, 0x11),
                (0, 1, 0x7FFF, 0x8000, 0xFFFF), WIDTHS, range(8), (0, 8)):
            models = self.compare(fixture(flags=flags, timer=timer, tick=tick),
                tuple(0 if mask & (1 << i) else 0x81234580 for i in range(3)), phase=phase)
            reached.update(models[2].visits)
            count += 1
        for flags, mask, mode, phase in itertools.product((0, 0x10), range(8), range(8), (0, 8)):
            self.compare(fixture(flags=flags), tuple(0 if mask & (1 << i) else 1 for i in range(3)), mode, phase)
            count += 1
        # The compiler's duplicated -1 constant at word 76 is structurally unreachable.
        self.assertEqual(reached, {screen.ENTRY + i * 4 for i in range(100) if i != 76})
        self.receipt('guest', dict(cases=count, executions=count * 3, reachable_words=99, unreachable_word=76,
            all_256_bytes_in_all_three_selectors=True, wrapped_signed_timer=True, full_callback_results=True,
            validation_not_skipped_after_failure=True, live_selectors_flags_tables=True,
            raw_normalized_retail_public_agreement=True, normalized_full_state_agreement=True,
            saved_GP_FP=True, four_outgoing_home_clobbers=True, void_V0_not_a_status_contract=True))

    def test_03_lazy_fields_tables_and_missing_public_byte_fault_prefixes(self):
        count = 0
        for selectors, flags, result, phase in itertools.product(((0, 0, 0xFF), (1, 1, 0), (15, 18, 8), (0, 18, 0)),
                (0, 0x10, 0x11), (0, 1), (0, 8)):
            memory = fixture(selectors, flags)
            results = (result, result, result)
            complete = TimerOracle(self.retail, memory, results, phase=phase).run()
            used = {e[1] + i for e in public(complete.events) if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(used):
                missing = dict(memory)
                del missing[address]
                models = [TimerOracle(body, missing, results, phase=phase) for body in (self.raw, self.words, self.retail)]
                self.assertEqual([outcome(model) for model in models], [False] * 3)
                for model in models[:2]:
                    self.assertEqual((external(model.memory), public(model.events), model.calls),
                        (external(models[2].memory), public(models[2].events), models[2].calls))
                count += 1
            minimal = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x140 or a in used}
            self.compare(minimal, results, phase=phase)
        self.receipt('faults', dict(missing_public_byte_triples=count, lazy_global_timer_third_selector_tables=True,
            fault_prefix_not_portable_C_or_hardware_acceptance=True, private_frame_aliases_not_claimed=True))

    def test_04_complete_forms_and_effective_semantic_negatives(self):
        negatives = {
            'negative-wrong-tick': screen.SELECTED.replace('- (u32)D_800BE9E4', '+ (u32)D_800BE9E4'),
            'negative-first-bound': screen.SELECTED.replace('first >= 15', 'first >= 14'),
            'negative-second-bound': screen.SELECTED.replace('second >= 18', 'second >= 17'),
            'negative-third-signedness': screen.SELECTED.replace('s8 action;', 'u8 action;'),
            'negative-ignore-first-failure': screen.SELECTED.replace('D_8008A200[first](actor) == 0', 'D_8008A200[first](actor) == 7'),
            'negative-stale-second': screen.SELECTED.replace('    first = actor[0x2F];', '    second = actor[0x30];\n    first = actor[0x2F];').replace('    second = actor[0x30];\n    if (second', '    if (second'),
        }
        samples = [(fixture(selectors=s, flags=f, timer=t, tick=k), r, m) for s, f, t, k, r, m in (
            ((1, 1, 0), 0x11, 0, 1, (1, 1, 1), 0), ((14, 1, 0), 0x10, 1, 1, (1, 1, 1), 0),
            ((1, 17, 0), 0x10, 1, 1, (1, 1, 1), 0), ((1, 1, 0xFF), 0x10, 1, 1, (1, 1, 1), 0),
            ((1, 1, 0), 0x10, 1, 1, (0, 1, 1), 0), ((1, 1, 0), 0x10, 1, 1, (1, 1, 1), 2),
            ((0, 0, 0), 0, 1, 1, (1, 1, 1), 0), ((1, 1, 0), 0x10, 1, 1, (1, 1, 1), 6))]
        records = []
        for name, body in [*screen.candidates(), *negatives.items()]:
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            failed = False
            for memory, results, mode in samples:
                TimerOracle(words, memory, results, mode).run()
                wanted, calls = reference(memory, results, mode)
                model = TimerOracle(words, memory, results, mode).run()
                failed |= (model.calls, external(model.memory)) != (calls, external(wanted))
            if name in negatives:
                self.assertTrue(failed, name)
            else:
                self.assertFalse(failed, name)
            records.append(dict(meta, semantic_difference=failed))
        self.receipt('forms', dict(compiled_complete_forms=len(records), ordinary=len(records) - len(negatives),
            samples_per_form=len(samples), effective_negatives=list(negatives), records=records))

    def test_05_owner_neighbors_actual_guarded_padding_and_four_independent_links(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, warning = compile_owner(self.root, self.out, text, 'owner-' + name)
            objects.append(obj)
            warnings.append(warning)
        self.assertEqual(warnings[0], warnings[1])
        old, before, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION:
                continue
            prev = before[name]
            self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']]), name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prev['value']: r for o, r in old_rel.items() if prev['value'] <= o < prev['value'] + prev['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        guard_file = self.out / 'candidate-guards.csv'
        with guard_file.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(baseline['guards'][0]))
            writer.writeheader()
            writer.writerows(baseline['guards'] + screen.guard_rows())
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/174BF0.s',
            word_patches_path=guard_file, filename='generated_174BF0')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 400)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS)
            if variant:
                base = (0x80007FF0, 0x80008000, 0x8000FFF0)[variant - 1]
                defs = {n: base + i * 0x1000 for i, n in enumerate(screen.SYMBOLS)}
                defs['func_1516972C'] = (entry & 0xF0000000) + 0x208000
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % (n, v) for n, v in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>100I', sections(elf)['.text'][1]))
            if not variant:
                self.assertEqual(words, self.retail)
            for flags, mask, mode, phase in itertools.product((0x10, 0x11), range(8), (0, 2, 6, 7), (0, 8)):
                self.compare(fixture(flags=flags, symbols=defs), tuple(0 if mask & (1 << i) else 1 for i in range(3)),
                    mode, phase, words, entry, defs)
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=len(warnings[0]),
            pools_and_relative_relocations_unchanged=True, actual_padding_bytes=400, target_guards=6,
            independent_links=4, cases=count))

    def test_06_whole_ELF_only_target_symbol_size_and_six_guard_rows_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, new = shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == new
        slots, functions = slot_records(self.root)
        expected = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        order_swap = []
        if installed:
            expected[screen.FUNCTION] = dict(address=screen.ENTRY, words=100,
                sha256=hashlib.sha256(struct.pack('>100I', *self.retail)).hexdigest())
            offset = layout.elf_slot_offset(data, screen.ENTRY, 400)
            data[offset:offset + 400] = struct.pack('>100I', *self.retail)
            offset = size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, offset)[0], 12)
            struct.pack_into('>I', data, offset, 400)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
            # Full rebuild reorders this exact pair; their logical symbol records do not change.
            before_symbols = sorted((name, symbol[1:]) for name, symbol, _, _ in symbol_records(data))
            actual_symbols = sorted((name, symbol[1:]) for name, symbol, _, _ in symbol_records(
                (self.root / 'conker/build/conker.us.elf').read_bytes()))
            self.assertEqual(actual_symbols, before_symbols)
            order_swap = exchange_absolute_symbol_order(data)
        self.assertEqual(slots, expected)
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), (self.out / 'before-progress.csv').read_bytes())
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        self.assertEqual(guards, baseline['guards'] + (screen.guard_rows() if installed else []))
        prefix = (self.out / 'before-retail_word_patches.us.csv').read_bytes()
        current = (self.root / 'conker/retail_word_patches.us.csv').read_bytes()
        self.assertTrue(current.startswith(prefix))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), guards=len(guards), old_guard_rows_unchanged=True,
            full_ELF_except_target_symbol_size_and_exact_ABS_order_swap_unchanged=True,
            all_logical_symbols_unchanged_except_target_size=True, absolute_symbol_order_swap=order_swap,
            symbol_size_change=[12, 400] if installed else None,
            progress_unchanged=True, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=guards, progress=baseline['progress']))

    def test_07_native32_timer_patterns_flags_selectors_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;typedef short s16;
typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
''' + screen.DECLARATIONS + r'''
s32 D_800BE9E4;
static union { u32 align;u8 b[256]; } storage,wanted;
static u32 values[3];static int mode,logCount,wantCount,error,logStages[4],wantStages[4];
static void mutate(u8 *p,int stage) {
    if(stage==0) {
        if(mode==1) p[0x30]=17;
        if(mode==2) p[0x30]=18;
        if(mode==3) *(u16 *)(p+0x1E)=0;
        if(mode==4) {*(u16 *)(p+0x1E)=0x10;p[0x24]=255;}
        if(mode==5) {*(u16 *)(p+0x1E)=0x10;p[0x24]=8;}
    } else if(stage==1) {
        if(mode==1) p[0x24]=7;
        if(mode==2) p[0x24]=254;
        if(mode==3) *(u16 *)(p+0x1E)=0x10;
        if(mode==4) p[0x24]=255;
        if(mode==5) *(u16 *)(p+0x1E)=0;
    }
}
static s32 called(u8 *p,int stage) {
    if(p!=storage.b || logCount>=4) {error=1;return 0;}
    logStages[logCount++]=stage;
    *(u32 *)(p+0x50)=0xCC000000u+(u32)stage;mutate(p,stage);
    return (s32)values[stage];
}
static s32 first(u8 *p) {return called(p,0);}
static s32 second(u8 *p) {return called(p,1);}
static s32 third(u8 *p) {return called(p,2);}
s32 (*D_8008A200[15])(u8 *);
s32 (*D_8008A23C[18])(u8 *);
s32 (*D_8008A284[8])(u8 *);
void func_1516972C(u8 *p) {
    if(p!=storage.b || logCount>=4) {error=2;return;}
    logStages[logCount++]=3;*(u32 *)(p+0x50)=0xDDDDDDDD;
}
static void model(void) {
    int stage,selector,expired=0;u8 *p=wanted.b;
    if(*(u16 *)(p+0x1E)&1) {
        u32 bits=(u32)*(s16 *)(p+0x1C)-(u32)D_800BE9E4;
        *(u16 *)(p+0x1C)=(u16)bits;expired=(bits&0x8000u)!=0;
    }
    for(stage=0;stage<3;stage++) {
        if(stage==2 && !(*(u16 *)(p+0x1E)&0x10)) break;
        selector=stage==2?(int)*(s8 *)(p+0x24):(int)p[stage==0?0x2F:0x30];
        if(selector>=(stage==0?15:stage==1?18:8) || (stage==2 && selector < -1)) {
            wantStages[wantCount++]=3;*(u32 *)(p+0x50)=0xDDDDDDDD;return;
        }
        if(selector!=(stage==2?-1:0) && !expired) {
            wantStages[wantCount++]=stage;*(u32 *)(p+0x50)=0xCC000000u+(u32)stage;
            mutate(p,stage);expired=values[stage]==0;
        }
    }
    if(expired) {wantStages[wantCount++]=3;*(u32 *)(p+0x50)=0xDDDDDDDD;}
}
''' + screen.SELECTED + r'''
static int check(u32 timer,u32 tick,u16 flags,int a,int b,int c,int mask,int change) {
    int i;u8 *p=storage.b;
    for(i=0;i<256;i++) p[i]=(u8)(i*17+0xA5);
    *(u16 *)(p+0x1C)=(u16)timer;*(u16 *)(p+0x1E)=flags;
    p[0x2F]=(u8)a;p[0x30]=(u8)b;p[0x24]=(u8)c;
    D_800BE9E4=(s32)tick;mode=change;logCount=wantCount=error=0;
    for(i=0;i<3;i++) values[i]=(mask&(1<<i))?0:0x80000001u+(u32)i;
    for(i=0;i<256;i++) wanted.b[i]=p[i];
    model();func_15147740(p);
    if(error || logCount!=wantCount) return 1;
    for(i=0;i<logCount;i++) if(logStages[i]!=wantStages[i]) return 2;
    for(i=0;i<256;i++) if(p[i]!=wanted.b[i]) return 3;
    return 0;
}
'''
        self.run_host(r'''
static u32 ticks[]={0,1,0x7FFF,0x8000,0xFFFF,0x10000,0xFFFF0001,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
int i,j,stage;u32 width;int selectors[3];
for(i=0;i<15;i++) D_8008A200[i]=first;
for(i=0;i<18;i++) D_8008A23C[i]=second;
for(i=0;i<8;i++) D_8008A284[i]=third;
for(width=0;width<65536;width++) for(j=0;j<10;j++)
    if(check(width,ticks[j],0x11,1,1,0,(int)(width>>5)&7,(int)(width%6))) return 1;
for(width=0;width<65536;width++)
    if(check(0x8000,0xFFFFFFFF,(u16)width,1,1,0,(int)(width>>5)&7,0)) return 2;
for(stage=0;stage<3;stage++) for(i=0;i<256;i++) {
    selectors[0]=selectors[1]=1;selectors[2]=0;selectors[stage]=i;
    if(check(1,1,0x10,selectors[0],selectors[1],selectors[2],0,0)) return 3;
}
''')
        self.receipt('native', dict(cases=65536 * 11 + 768, all_65536_timer_patterns=True,
            all_65536_flag_patterns=True, all_three_selector_bytes=True, full_word_tick_results=True,
            helper_mutations=True, canary_bytes=256, source_void=True,
            callback_cleanup_fixtures_not_hardware_or_gameplay_acceptance=True))

    def test_08_protected_actual_callback_table_identities_and_pointer_witnesses(self):
        elf = self.root / 'conker/build/conker.us.elf'
        base, data = load_section(elf, '.game_data')
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        tables = [struct.unpack_from('>%dI' % count, data, screen.SYMBOLS[name] - base) for name, count in zip(TABLES, BOUNDS)]
        self.assertEqual(tables, [
            (0, 0x15147EB8, 0x15196748, 0x1519D240, 0x150DC558, 0x1519F4F0, 0x151A361C, 0x150B40E8,
             0x1515C388, 0x151CD674, 0x151BC64C, 0x151B6420, 0x15199A10, 0x151D792C, 0x150D8E4C),
            (0, 0x150D8FAC, 0x15196B4C, 0x1519D454, 0x150DCEA0, 0x1519F7F0, 0x151A37C0, 0x150B4294,
             0x1515C534, 0x151CD7BC, 0x151BC794, 0x151B65D4, 0x15199C34, 0x150D3A68, 0x151B77F4,
             0x151CEC54, 0x151D7A38, 0x151D15D0),
            (0x1519A9A4, 0x150D3FD4, 0x151B7998, 0x151CF120, 0x151D7CD0, 0x150D942C, 0x151D197C, 0x151CDB94)])
        roles = {target: stage for stage, table in enumerate(tables) for target in table if target}
        self.assertEqual(len(roles), 39)
        _, functions = slot_records(self.root)
        self.assertTrue(all('func_%08X' % target in functions for target in roles))
        cases = 0
        for stage, selector, mask, phase in itertools.product(range(3), range(18), range(8), (0, 8)):
            if selector >= BOUNDS[stage]:
                continue
            selectors = [1, 1, 0]
            selectors[stage] = selector
            memory = fixture(selectors=selectors)
            for name, table in zip(TABLES, tables):
                for i, target in enumerate(table):
                    put(memory, screen.SYMBOLS[name] + i * 4, target)
            self.compare(memory, tuple(0 if mask & (1 << i) else 0x80000000 for i in range(3)), phase=phase, roles=roles)
            cases += 1
        refs = [base + i for i in range(0, len(data) - 3, 4) if struct.unpack_from('>I', data, i)[0] == screen.ENTRY]
        self.assertEqual(refs, [0x8008BB90, 0x8008C44C])
        self.receipt('tables', dict(entries=41, nonnull_targets=39, cases=cases,
            incoming_pointer_witnesses=[hex(a) for a in refs], targets=[[hex(t) for t in table] for table in tables],
            actual_callback_bodies_and_upstream_dispatch_not_executed=True))


if __name__ == '__main__':
    unittest.main()
