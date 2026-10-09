"""Complete callback update semantics, closed predicate order and owner audit."""

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

from tools.experiments import game_record_callback_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_attachment_allocation_match as allocation
from tools.tests import test_game_random_curve_record as native
from tools.tests import test_game_record_ring_shaping_recovery as shaping
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

OWNER, ATTACHED, ALT = 0x20000, 0x21000, 0x22000
CALLBACK, OTHER_CALLBACK = 0x15001000, 0x15002000
SOURCE = 'conker/src/game/generated_204660.c'
INSERT = screen.DECLARATIONS[:screen.DECLARATIONS.index('f32 func_15143E64')] + '\n'
MARKER = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
FLAGS = (0, 1, 127, 128, 254, 255)
LENGTHS = (0, 0x40800000, 0x40A00000, 0x40A00001, 0x7F800000, 0x7FC00001)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    original = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    assert original.count(screen.ORIGINAL) == 1 and original.count(MARKER) == 1
    return original, original.replace(MARKER, INSERT + MARKER).replace(screen.ORIGINAL, screen.SELECTED)


def public(events):
    return [event for event in events if event[0] == 'CALL' or not STACK - 0x600 <= event[1] < STACK + 0x140]


def external(memory):
    return {address: value for address, value in memory.items() if not STACK - 0x600 <= address < STACK + 0x140}


def fixture(selector=0, flag=1, attached=0, threshold=0x40A00000, table=None):
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, size in ((OWNER, 0x100), (ATTACHED, 0xB0), (ALT, 0xC0)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(size)})
    table = screen.SYMBOLS['D_8008FCA0'] if table is None else table
    for index in range(-128, 256):
        put(memory, table + index * 4, (CALLBACK if index >= 0 else OTHER_CALLBACK) + (index & 3) * 0x100)
    for address, value, size in ((OWNER + 0x28, attached, 4), (OWNER + 0x2C, selector, 1),
            (OWNER + 0x2D, flag, 1), (OWNER + 0xD, 0xA0, 1),
            (OWNER + 0xE, 0x1234, 2), (OWNER + 0x3C, threshold, 4)):
        put(memory, address, value, size)
    for axis, value in enumerate((1., -2., 4.)):
        put(memory, OWNER + 0x30 + axis * 4, bits(value))
    return memory


def actions(role, mode, table):
    if role == 'callback':
        return {
            0: [], 1: [(OWNER + 0x2D, 0, 1)], 2: [(OWNER + 0x2D, 1, 1)],
            3: [(OWNER + 0x30 + i * 4, bits(v), 4) for i, v in enumerate((5., 6., -8.))],
            4: [(OWNER + 0x28, ATTACHED, 4)],
            5: [(OWNER + 0x2C, 255, 1), (table, OTHER_CALLBACK, 4)],
            6: [(OWNER + 0xD, 0x7E, 1)],
            7: [], 8: [],
        }[mode]
    if role == 'distance':
        return {7: [(OWNER + 0x3C, bits(3.), 4)], 8: [(OWNER + 0x28, ATTACHED, 4)]}.get(mode, [])
    return []


class CallbackReference:
    def __init__(self, memory, result=1, length=0x40800000, mode=0, symbols=None):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.result, self.length, self.mode = result, length, mode
        self.symbols = symbols or screen.SYMBOLS

    def get(self, address, size=4):
        assert address % size == 0, ('unaligned read', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value, size=4):
        value &= (1 << (size * 8)) - 1
        self.events.append(('W', address, size, value))
        assert address % size == 0, ('unaligned store', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def call(self, target, args):
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        role = 'callback' if CALLBACK <= target < OTHER_CALLBACK + 0x400 else 'distance' if target == self.symbols['func_15143E64'] else 'other'
        for address, value, size in actions(role, self.mode, self.symbols['D_8008FCA0']):
            self.put(address, value, size)
        if target == self.symbols['func_151D77C8']:
            self.put(OWNER + 0x28, 0)
        elif target == self.symbols['func_151D7830']:
            self.put(OWNER + 0x28, ALT)

    def run(self):
        previous = [self.get(OWNER + 0x30 + axis * 4) for axis in range(3)]
        prior_flag = self.get(OWNER + 0x2D, 1) & 1
        selector = self.get(OWNER + 0x2C, 1)
        target = self.get(self.symbols['D_8008FCA0'] + selector * 4)
        self.call(target, (OWNER,))
        if not self.result:
            flags = self.get(OWNER + 0xD, 1)
            self.put(OWNER + 0xE, 65535, 2)
            self.put(OWNER + 0xD, flags | 1, 1)
            return self
        if not self.get(OWNER + 0x2D, 1) & 1 or not prior_flag:
            self.call(self.symbols['func_151D77C8'], (OWNER,))
            return self
        delta = tuple(bits(floating(self.get(OWNER + 0x30 + i * 4)) - floating(previous[i])) for i in range(3))
        self.call(self.symbols['func_15143E64'], delta)
        threshold = self.get(OWNER + 0x3C)
        if floating(self.length) < floating(threshold):
            if not self.get(OWNER + 0x28):
                self.call(self.symbols['func_151D7830'], (OWNER,))
        else:
            self.call(self.symbols['func_151D77C8'], (OWNER,))
        return self


class CallbackOracle(shaping.ShapingOracle):
    def __init__(self, words, memory, result=1, length=0x40800000, mode=0, phase=0, entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry, arguments=(OWNER,), connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.result, self.length, self.mode = result, length, mode
        self.symbols = symbols or screen.SYMBOLS

    def record_call(self, target):
        if target == self.symbols['func_15143E64']:
            assert STACK - 0x600 <= self.r[4] < STACK
            args = tuple(read(self.memory, self.r[4] + i * 4) for i in range(3))
        else:
            args = (self.r[4],)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if CALLBACK <= target < OTHER_CALLBACK + 0x400:
            role, result = 'callback', self.result
        elif target == self.symbols['func_15143E64']:
            role, result = 'distance', 0xA5000002
        else:
            assert target in (self.symbols['func_151D77C8'], self.symbols['func_151D7830']), hex(target)
            role, result = 'other', 0xA5000002
            self.put(OWNER + 0x28, 0 if target == self.symbols['func_151D77C8'] else ALT, 4)
        for address, value, size in actions(role, self.mode, self.symbols['D_8008FCA0']):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result & 0xFFFFFFFF
        if role == 'distance':
            self.f[0] = self.length


def outcome(model):
    try:
        model.run()
        return True
    except AssertionError as error:
        assert isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return False


class GameRecordCallbackUpdateMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-callback-update-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>81I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, result=1, length=0x40800000, mode=0, phase=0, raw=True):
        ref = CallbackReference(memory, result, length, mode)
        complete = outcome(ref)
        models = [CallbackOracle(body, memory, result, length, mode, phase)
            for body in ((self.words, self.retail, self.raw) if raw else (self.words, self.retail))]
        for model in models:
            self.assertEqual(outcome(model), complete)
            self.assertEqual((external(model.memory), public(model.events), model.calls),
                (external(ref.memory), ref.events, ref.calls))
        self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events, models[0].calls),
            (models[1].r, models[1].f, models[1].memory, models[1].events, models[1].calls))
        return models[0], complete

    def test_01_complete_slot_profiles_and_closed_stale_block(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (81, 64, 9))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
        expected = {0x28: [('R_MIPS_HI16', 'D_8008FCA0')], 0x4C: [('R_MIPS_LO16', 'D_8008FCA0')],
            0xCC: [('R_MIPS_26', 'func_15143E64')], 0xFC: [('R_MIPS_26', 'func_151D7830')],
            **{pc: [('R_MIPS_26', 'func_151D77C8')] for pc in (0x10C, 0x11C, 0x12C)}}
        self.assertEqual(self.record['relocations'], expected)
        for index in range(0x78 // 4, 0x9C // 4):
            changed = list(self.raw)
            changed[index] ^= 1
            with self.assertRaisesRegex(ValueError, 'stale complete callback predicate'):
                screen.normalize(changed)
        with self.assertRaises(ValueError):
            screen.normalize(self.raw[:-1])
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in PROFILES]
        self.assertEqual([(m['body_words'], m['frame'], m['differences']) for m in profiles],
            [(81, 64, 9), (79, 64, 77), (84, 56, 77), (84, 56, 78)])
        self.receipt('slot', dict(words=81, bytes=324, direct_words=72, guards=9,
            relocation_uses=7, profiles=profiles, derived_reorder_without_retail_lookup=True))

    def test_02_full_unsigned_selector_live_mutations_and_float_edges(self):
        cases, seen = 0, set()
        for selector in range(256):
            for result in (0, 1, 0x80000000):
                model, complete = self.compare(fixture(selector), result, mode=selector % 9)
                self.assertTrue(complete)
                seen.update(model.visits)
                cases += 1
        for flag, result, length, mode, attached, phase in itertools.product(FLAGS, (0, 1), LENGTHS,
                range(9), (0, ATTACHED), (0, 8)):
            model, complete = self.compare(fixture(128, flag, attached), result, length, mode, phase)
            self.assertTrue(complete)
            seen.update(model.visits)
            cases += 1
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 324, 4)))
        self.receipt('guest', dict(cases=cases, executions=cases * 3, all_256_unsigned_selectors=True,
            all_81_words_reached=True, modes=9, raw_public_prefixes_and_complete_derived_retail_state=True,
            strict_threshold_equality_nan_and_infinity=True, void_return_contract=True))

    def test_03_lazy_reads_and_real_missing_byte_fault_prefixes(self):
        pairs, lazy = 0, 0
        for flag, result, mode, length in itertools.product((0, 1), (0, 1), (0, 3, 7, 8), (0x40800000, 0x40A00000)):
            memory = fixture(flag=flag)
            ref = CallbackReference(memory, result, length, mode).run()
            required = {e[1] + i for e in ref.events if e[0] in ('R', 'W') for i in range(e[2])}
            trimmed = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x140 or a in required}
            self.assertTrue(self.compare(trimmed, result, length, mode)[1])
            lazy += 1
            first = set()
            seen = set()
            for event in ref.events:
                if event[0] not in ('R', 'W'):
                    continue
                for a in range(event[1], event[1] + event[2]):
                    if event[0] == 'R' and a not in seen:
                        first.add(a)
                    seen.add(a)
            for address in first:
                broken = dict(memory)
                del broken[address]
                self.assertFalse(self.compare(broken, result, length, mode, raw=False)[1])
                pairs += 1
        self.receipt('faults', dict(pairs=pairs, lazy_cases=lazy,
            complete_normalized_retail_model_state_equal=True, portable_C_or_hardware_faults=False))

    def test_04_complete_forms_and_effective_compiled_negatives(self):
        records, negatives, prefix_changes = [], [], []
        samples = [(fixture(128, flag), result, length, mode)
            for flag, result, length, mode in itertools.product((0, 1), (0, 1),
                (0x40800000, 0x40A00000, 0x7FC00001), (0, 2, 3, 6, 8))]
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            equal, prefixes = [], []
            for memory, result, length, mode in samples:
                ref = CallbackReference(memory, result, length, mode)
                expected = outcome(ref)
                model = CallbackOracle(words, memory, result, length, mode)
                complete = outcome(model)
                equal.append((complete, external(model.memory), model.calls) ==
                    (expected, external(ref.memory), ref.calls))
                prefixes.append(public(model.events) == ref.events)
            if name.startswith('negative-'):
                self.assertFalse(all(equal), name)
                negatives.append(name)
            else:
                self.assertTrue(all(equal), name)
                if not all(prefixes):
                    prefix_changes.append(name)
        self.receipt('forms', dict(forms=len(records), compiled_negatives=negatives, samples=len(samples),
            exploratory_forms_with_different_prefixes=prefix_changes, selected_prefix_checked_separately=True, measurements=records))

    def test_05_real_copied_owner_padder_and_independent_symbol_links(self):
        objects, diagnostics = [], []
        for name, source in zip(('baseline', 'selected'), source_shapes(self.root)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            processed = self.out / ('owner-' + name + '-post.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION:
                continue
            before = previous[name]
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[before['value']:before['value'] + before['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - before['value']: r for o, r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        fn = current[screen.FUNCTION]
        copied = list(struct.unpack_from('>81I', text, fn['value']))
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        before = json.loads((self.out / 'baseline.json').read_text())
        self.assertEqual(rows[:11460], before['guards'])
        guards = screen.owner_guards(copied)
        self.assertEqual(len(guards), 9)
        self.assertIn(rows[11460:], ([], guards))
        manifest = self.out / 'proposed.csv'
        def emit(suffix):
            with manifest.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows[:11460] + suffix)
            return emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
                word_patches_path=manifest, filename='generated_204660')
        for index in range(9):
            stale = [dict(row) for row in guards]
            stale[index]['expected'] = '0x%08X' % (int(stale[index]['expected'], 0) ^ 1)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit(stale)
        assembly = emit(guards)
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, symbols, relocations = parse_object(obj)
        self.assertEqual((symbols[screen.FUNCTION]['size'], relocations), (324, self.record['relocations']))
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            defs = dict(screen.SYMBOLS)
            defs['D_8008FCA0'] = (0x8008FCA0, 0x70007FFC, 0x70108000, 0x7020FFF8)[variant]
            if variant:
                for i, name in enumerate(n for n in defs if n.startswith('func_')):
                    defs[name] = (entry & 0xF0000000) + 0x100800 + i * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = self.out / ('rebase-%d.elf' % variant)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            body = list(struct.unpack_from('>81I', sections(elf)['.text'][1]))
            for selector, flag, result, mode in itertools.product((0, 128, 255), (0, 1), (0, 1), (0, 3, 8)):
                memory = fixture(selector, flag, table=defs['D_8008FCA0'])
                ref = CallbackReference(memory, result, mode=mode, symbols=defs).run()
                model = CallbackOracle(body, memory, result, mode=mode, entry=entry, symbols=defs).run()
                self.assertEqual((external(model.memory), public(model.events), model.calls),
                    (external(ref.memory), ref.events, ref.calls))
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, pools_relocations_and_diagnostics_unchanged=True,
            guards=9, stale_guard_controls=9, padded_bytes=324, independent_links=4, executions=count))

    def test_06_current_linked_baseline_or_installed_closure(self):
        before = json.loads((self.out / 'baseline.json').read_text())
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(hashlib.sha256(elf.read_bytes()).hexdigest(), before['elf_sha256'])
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(struct.pack('>%dI' % len(w), *w)).hexdigest())
            for n, w in functions.items()}
        self.assertEqual(slots, before['slots'])
        source = (self.root / SOURCE).read_text()
        original, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(), before['source_sha256'])
        self.assertIn(source, (original, selected))
        self.assertEqual(functions[screen.FUNCTION], self.retail)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[:11460], before['guards'])
        self.assertEqual(rows[11460:], screen.owner_guards(self.raw) if source == selected else [])
        with (self.root / 'conker/progress.csv').open(newline='') as stream:
            progress = list(csv.DictReader(stream))
        expected = [dict(r, language='c') if r['function'] == screen.FUNCTION and source == selected else r for r in before['progress']]
        self.assertEqual(progress, expected)
        self.receipt('linked', dict(installed=source == selected, symbols=len(slots),
            complete_ELF_unchanged=True, guards=len(rows), one_conversion_row=source == selected))

    def test_07_actual_native32_C_all_flag_selector_pairs_and_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.DECLARATIONS + screen.SELECTED + NATIVE_CHECK
        self.run_host('unsigned flag,selector,mode,r,l,a;\n'
            'if(sizeof(void*)!=4 || sizeof(CallbackRecord151D7264)!=24)return 10;\n'
            'for(flag=0;flag<256;flag++)for(selector=0;selector<256;selector++)'
            'if(check(selector,flag,1,0x40800000,0,0,0xA0))return 11;\n'
            'for(flag=0;flag<6;flag++)for(r=0;r<3;r++)for(l=0;l<6;l++)for(mode=0;mode<9;mode++)for(a=0;a<2;a++)'
            'if(check(128,flags[flag],results[r],lengths[l],mode,a,0xA0))return 12;\n'
            'for(flag=0;flag<256;flag++)if(check(255,1,0,0x40800000,0,0,flag))return 13;')
        self.receipt('native', dict(cases=65536 + 6 * 3 * 6 * 9 * 2 + 256,
            all_65536_flag_selector_pairs=True, all_failure_flag_bytes=True,
            actual_C_volatile_typed_call=True, full_512_byte_canaries=True, modes=9,
            callback_and_distance_are_bounded_mutable_helpers=True))

    def test_08_actual_callback_table_magnitude_and_attached_clear(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        pool_address, pool = sections(self.root / 'conker/build/conker.us.elf')['.game_data']
        table = screen.SYMBOLS['D_8008FCA0']
        actual = list(struct.unpack_from('>5I', pool, table - pool_address))
        self.assertEqual(actual, [0x151D75C4, 0x151D7538, 0x151D7724, 0x151D7770, 0x151D779C])
        selected = ('func_151D7724', 'func_151D7770', 'func_151D779C', 'func_15143E64', 'func_151D77C8')
        self.assertEqual([len(functions[n]) for n in selected], [19, 11, 11, 12, 26])
        connected = {addresses[n] + i * 4: w for n in selected for i, w in enumerate(functions[n])}
        cases, seen = 0, set()
        actor = 0x24000
        for selector, kind, actor_flag, prior_flag, phase in itertools.product((2, 3, 4), (0, 4, 10, 12, 13),
                (0, 2), (0, 1), (0, 8)):
            memory = fixture(selector, prior_flag, ATTACHED, threshold=bits(-1.))
            memory.update({actor + i: 0 for i in range(0x400)})
            for i, target in enumerate(actual):
                put(memory, table + i * 4, target)
            for address, value, size in ((OWNER + 0x40, actor, 4), (actor + 0x94, actor_flag, 4),
                    (actor + 0x84, kind, 2), (actor + 0xAD, actor_flag, 1),
                    (ATTACHED + 0x98, ALT, 4), (ATTACHED + 0x1E, 0xFFFF, 2)):
                put(memory, address, value, size)
            models = [CallbackOracle(body, memory, phase=phase, connected=connected).run()
                for body in (self.raw, self.words, self.retail)]
            for model in models:
                self.assertEqual(read(model.memory, OWNER + 0x28), 0)
                self.assertEqual(read(model.memory, ATTACHED + 0x30, 1), 0)
                self.assertEqual(read(model.memory, ATTACHED + 0x1E, 2), 0xFFFD)
                self.assertEqual(read(model.memory, ATTACHED + 0x1C, 2), 20)
                self.assertEqual(read(model.memory, ALT), 0)
                seen.update(model.visits)
            self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                (external(models[2].memory), public(models[2].events), models[2].calls))
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events, models[1].calls),
                (models[2].r, models[2].f, models[2].memory, models[2].events, models[2].calls))
            cases += 1
        self.assertTrue(set(range(0x15143E64, 0x15143E94, 4)) <= seen)
        self.receipt('connected', dict(cases=cases, executions=cases * 3, real_table_slots=[2, 3, 4],
            complete_callbacks_words=[19, 11, 11], complete_magnitude_words=12, complete_clear_words=26,
            all_magnitude_words_reached=True, full_constructor_allocation_arm_separate=True,
            table_slots_0_and_1_not_qualified=True, hardware_gameplay=False))

    def test_09_full_constructor_allocation_connection(self):
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        allocator = list(struct.unpack_from('>67I', rom, allocation.screen.ROM))
        constructor = list(struct.unpack_from('>115I', rom, 0x174F30))
        connected = {allocation.screen.ENTRY + i * 4: w for i, w in enumerate(allocator)}
        connected.update({allocation.screen.SYMBOLS['func_15147A80'] + i * 4: w for i, w in enumerate(constructor)})
        cases = 0
        for record, phase, byte in itertools.product((0, allocation.RECORD), (0, 8), (0, 127, 128, 255)):
            memory = allocation.fixture(byte, 255 - byte, 4)
            put(memory, OWNER + 0x2C, 0, 1)
            put(memory, OWNER + 0x2D, 1, 1)
            put(memory, OWNER + 0x3C, bits(1.))
            put(memory, screen.SYMBOLS['D_8008FCA0'], allocation.CALLBACK)
            models = [allocation.AllocationOracle(body, memory, record, phase=phase,
                entry=screen.ENTRY, connected=connected).run() for body in (self.raw, self.words, self.retail)]
            for model in models:
                self.assertEqual(read(model.memory, OWNER + 0x28), record)
                self.assertEqual([args for role, args in model.raw_calls if role == 'allocator'],
                    [(0x4D, 255 - byte, 892, 1, byte, 1)])
                if record:
                    self.assertEqual(read(model.memory, record + 0x98), record + 0xA0)
                    self.assertEqual(read(model.memory, record + 0x94), record + 0xC0)
                    self.assertEqual(tuple(read(model.memory, record + 0xA0 + 4 * i) for i in range(7)),
                        (OWNER, *[read(memory, OWNER + 0x30 + i * 4) for i in range(3)], 0, 0, 0))
            self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                (external(models[2].memory), public(models[2].events), models[2].calls))
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events, models[1].calls),
                (models[2].r, models[2].f, models[2].memory, models[2].events, models[2].calls))
            cases += 1
        self.receipt('allocation', dict(cases=cases, executions=cases * 3, complete_allocation_words=67,
            complete_constructor_words=115, null_and_valid_allocations=True, allocator_copy_zero_bounded=True,
            linked_constructor_still_false_zero_placeholder=True, hardware_gameplay=False))

    def test_10_effective_partial_predicate_negatives(self):
        witnesses = []
        for offset, memory, mode in ((0x78, fixture(), 0), (0x88, fixture(), 1)):
            changed = list(self.words)
            changed[offset // 4] = self.raw[offset // 4]
            model = CallbackOracle(changed, memory, mode=mode)
            complete = outcome(model)
            reference = CallbackReference(memory, mode=mode).run()
            self.assertFalse(complete and (external(model.memory), model.calls) ==
                (external(reference.memory), reference.calls))
            witnesses.append(dict(offset=offset, completed=complete, actual_fault_or_changed_calls=True))
        self.receipt('partial-negatives', dict(witnesses=witnesses, no_timeout_or_unsupported_opcode=True))

    def test_11_rebased_table_owner_aliases_preserve_captured_and_live_values(self):
        cases = 0
        for offset in (0xC, 0x28, 0x30, 0x3C):
            defs = dict(screen.SYMBOLS, D_8008FCA0=OWNER + offset)
            script, elf = self.out / 'alias.ld', self.out / ('alias-%X.elf' % offset)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % screen.ENTRY)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(self.out / 'selected.o')],
                check=True, capture_output=True)
            raw = list(struct.unpack_from('>81I', sections(elf)['.text'][1]))
            normalized = screen.normalize(raw)
            for result, mode, phase in itertools.product((0, 1), (0, 3, 4, 5, 7, 8), (0, 8)):
                memory = fixture(table=defs['D_8008FCA0'])
                put(memory, defs['D_8008FCA0'], CALLBACK)
                ref = CallbackReference(memory, result, mode=mode, symbols=defs).run()
                for body in (raw, normalized):
                    model = CallbackOracle(body, memory, result, mode=mode, phase=phase, symbols=defs).run()
                    self.assertEqual((external(model.memory), public(model.events), model.calls),
                        (external(ref.memory), ref.events, ref.calls))
                cases += 1
        self.receipt('aliases', dict(cases=cases, independently_linked_table_layouts=4,
            aliases=['failure fields', 'attached slot', 'captured position', 'live threshold'],
            raw_and_normalized_public_prefixes_equal=True, invalid_pointer_portable_C_acceptance=False))


NATIVE_PREFIX = r'''
typedef signed char s8;typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void *)0)
static u8 arena[512] __attribute__((aligned(16))),expected[512] __attribute__((aligned(16)));
static u8 *owner=arena+32,*attached=arena+256,*fresh=arena+384;
static unsigned mode,lenBits,cbResult,cbId,cbCount,distanceCount,clearCount,allocCount;
static int error;
static f32 number(u32 v){union{u32 u;f32 f;} x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;} x;x.f=v;return x.u;}
static void change(u8 *p,unsigned role){
 if(!role){
  if(mode==1)p[0x2D]=0;
  if(mode==2)p[0x2D]=1;
  if(mode==3){*(f32*)(p+0x30)=5;*(f32*)(p+0x34)=6;*(f32*)(p+0x38)=-8;}
  if(mode==4)*(u8**)(p+0x28)=attached;
  if(mode==5)p[0x2C]=255;
  if(mode==6)p[0xD]=0x7E;
 }else{if(mode==7)*(f32*)(p+0x3C)=3;if(mode==8)*(u8**)(p+0x28)=attached;}
}
'''


NATIVE_CHECK = r'''
static s32 callback(u8 *p,unsigned id){
 if(p!=owner||cbCount||distanceCount||clearCount||allocCount)error=1;
 cbId=id;cbCount++;change(p,0);return (s32)cbResult;
}
static s32 cb0(u8*p){return callback(p,0);}static s32 cb1(u8*p){return callback(p,1);}
static s32 cb2(u8*p){return callback(p,2);}static s32 cb3(u8*p){return callback(p,3);}
s32 (*D_8008FCA0[256])(u8*);
f32 func_15143E64(f32 *p){
 unsigned i;static const f32 delta[]={4,8,-12};
 if(cbCount!=1||distanceCount||clearCount||allocCount)error=2;
 for(i=0;i<3;i++)if(word(p[i])!=word(mode==3?delta[i]:0.0f))error=3;
 distanceCount++;change(owner,1);return number(lenBits);
}
void func_151D77C8(u8*p){if(p!=owner||cbCount!=1||clearCount||allocCount)error=4;clearCount++;*(u8**)(p+0x28)=NULL;}
void func_151D7830(u8*p){if(p!=owner||cbCount!=1||clearCount||allocCount)error=5;allocCount++;*(u8**)(p+0x28)=fresh;}
static unsigned flags[]={0,1,127,128,254,255},results[]={0,1,0x80000000};
static unsigned lengths[]={0,0x40800000,0x40A00000,0x40A00001,0x7F800000,0x7FC00001};
static int check(unsigned selector,unsigned flag,unsigned result,unsigned length,unsigned mutation,unsigned hasAttached,unsigned failFlag){
 unsigned i,dist=0,clear=0,alloc=0;u8 *e=expected+32;
 void (*volatile fn)(u8*)=func_151D7264;
 for(i=0;i<512;i++)arena[i]=(u8)(i*17+0xA5);
 for(i=0;i<256;i++)D_8008FCA0[i]=(i&3)==0?cb0:(i&3)==1?cb1:(i&3)==2?cb2:cb3;
 owner[0x2C]=(u8)selector;owner[0x2D]=(u8)flag;owner[0xD]=(u8)failFlag;*(s16*)(owner+0xE)=0x1234;
 *(u8**)(owner+0x28)=hasAttached?attached:NULL;
 *(f32*)(owner+0x30)=1;*(f32*)(owner+0x34)=-2;*(f32*)(owner+0x38)=4;*(f32*)(owner+0x3C)=5;
 for(i=0;i<512;i++)expected[i]=arena[i];
 mode=mutation;cbResult=result;lenBits=length;error=0;cbCount=distanceCount=clearCount=allocCount=0;
 change(e,0);
 if(!result){*(s16*)(e+0xE)=-1;e[0xD]|=1;}
 else if((flag&1)&&(e[0x2D]&1)){
  dist=1;change(e,1);
  if(number(length)<*(f32*)(e+0x3C)){
   if(*(u8**)(e+0x28)==NULL){alloc=1;*(u8**)(e+0x28)=fresh;}
  }else{clear=1;*(u8**)(e+0x28)=NULL;}
 }else{clear=1;*(u8**)(e+0x28)=NULL;}
 fn(owner);
 if(error||cbCount!=1||cbId!=(selector&3)||distanceCount!=dist||clearCount!=clear||allocCount!=alloc)return 1;
 for(i=0;i<512;i++)if(arena[i]!=expected[i])return 2;
 return 0;
}
'''


if __name__ == '__main__':
    unittest.main()
