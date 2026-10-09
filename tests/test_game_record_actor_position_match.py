"""Whole-entry actor callback, lazy reads, frame closure and actual owner matching."""

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

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_record_actor_position_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read, PointOracle, STATUS, FLAG
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests import test_game_random_curve_record as native
from tools.tests import test_game_record_ring_shaping_recovery as shaping
from tools.tests import test_game_point_transform_match as point
from tools.tests import test_game_record_callback_update_match as callback_update
from tools.tests.game_animation_timeline_oracle import bits, floating

OWNER, ACTOR, SECONDARY, MATRICES, ALTERNATE = 0x20000, 0x21000, 0x22000, 0x30000, 0x24000
CALLBACK, NEGATIVE_CALLBACK = 0x15001000, 0x15002000
SOURCE = 'conker/src/game/generated_204660.c'
MARKER = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
INSERT = screen.DECLARATIONS + '\n'


def source_shapes(root):
    source = (root / SOURCE).read_text()
    original = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    assert original.count(screen.ORIGINAL) == 1 and original.count(MARKER) == 1
    return original, original.replace(MARKER, INSERT + MARKER).replace(screen.ORIGINAL, screen.SELECTED)


def fixture(joint=0, callback=255, flags=0xA4, gate=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, length in ((OWNER, 0x100), (ACTOR, 0x400), (SECONDARY, 0x200), (ALTERNATE, 0x400),
            (symbols['D_800AB280'], 256 * 12), (symbols['D_8008FCA8'] - 512, 1536)):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(length)})
    for index in range(-128, 256):
        put(memory, symbols['D_8008FCA8'] + index * 4, NEGATIVE_CALLBACK if index < 0 else CALLBACK)
    for index in range(256):
        put(memory, symbols['D_800AB2D4'] + index, (index * 3 + 1) & 255, 1)
    fields = ((OWNER + 0x40, ACTOR, 4), (OWNER + 0x44, 7, 1), (OWNER + 0x45, joint, 1),
        (OWNER + 0x46, callback, 1), (OWNER + 0x2D, flags, 1),
        (ACTOR, 0 if gate == 1 else 0x80000000, 4), (ACTOR + 0x3B, 8 if gate == 2 else 7, 1),
        (ACTOR + 0x1D4, 0 if gate == 3 else MATRICES, 4),
        (ACTOR + 0x31C, SECONDARY if gate in (4, 5, 6) else 0, 4),
        (SECONDARY + 0x197, 0 if gate == 5 else 0x80, 1),
        (ACTOR + 0x318, 0 if gate == 6 else ALTERNATE, 4), (ACTOR + 7, 0 if gate == 7 else 255, 1))
    for address, value, size in fields:
        put(memory, address, value, size)
    return memory


def mutations(mode):
    return {0: (), 1: ((OWNER + 0x2D, 0xFE, 1),), 2: ((OWNER + 0x46, 255, 1),),
        3: ((OWNER + 0x46, 128, 1),), 4: ((OWNER + 0x40, ALTERNATE, 4),),
        5: ((OWNER + 0x45, 255, 1), (OWNER + 0x2D, 0, 1))}[mode]


class PositionReference:
    def __init__(self, memory, mode=0, result=0x87654321, symbols=None):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.mode, self.callback_result = mode, result
        self.symbols = symbols or screen.SYMBOLS
        self.result = None

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
        if target == self.symbols['func_15143134']:
            point, output, _ = args
            for axis in range(3):
                self.put(output + axis * 4, self.get(point + axis * 4))
            for address, value, size in mutations(self.mode):
                self.put(address, value, size)
        else:
            assert target in (CALLBACK, NEGATIVE_CALLBACK)
            self.put(OWNER + 0x47, target == NEGATIVE_CALLBACK, 1)

    def run(self):
        actor = self.get(OWNER + 0x40)
        if not self.get(actor) or self.get(OWNER + 0x44, 1) != self.get(actor + 0x3B, 1):
            self.result = 0
            return self
        matrices = self.get(actor + 0x1D4)
        clear = not matrices
        if not clear:
            secondary = self.get(actor + 0x31C)
            clear = bool(secondary and self.get(secondary + 0x197, 1) and self.get(actor + 0x318))
            if not clear:
                clear = self.get(actor + 7, 1) != 255
        if clear:
            self.put(OWNER + 0x2D, self.get(OWNER + 0x2D, 1) & 254, 1)
            self.result = 1
            return self
        joint = self.get(OWNER + 0x45, 1)
        mapped = self.get(self.symbols['D_800AB2D4'] + joint, 1)
        self.call(self.symbols['func_15143134'], (self.symbols['D_800AB280'] + joint * 12,
            OWNER + 0x30, (matrices + mapped * 64) & 0xFFFFFFFF))
        self.put(OWNER + 0x2D, self.get(OWNER + 0x2D, 1) | 1, 1)
        callback = self.get(OWNER + 0x46, 1)
        callback = callback if callback < 128 else callback - 256
        if callback != -1:
            target = self.get((self.symbols['D_8008FCA8'] + callback * 4) & 0xFFFFFFFF)
            self.call(target, (OWNER,))
            self.result = self.callback_result & 0xFFFFFFFF
        else:
            self.result = 1
        return self


class PositionOracle(shaping.ShapingOracle):
    def __init__(self, words, memory, mode=0, result=0x87654321, phase=0, entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry, arguments=(OWNER,), connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.mode, self.callback_result = mode, result
        self.symbols = symbols or screen.SYMBOLS

    def record_call(self, target):
        args = tuple(self.r[4:7]) if target == self.symbols['func_15143134'] else (self.r[4],)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == self.symbols['func_15143134']:
            point, output, _ = self.r[4:7]
            for axis in range(3):
                self.put(output + axis * 4, self.get(point + axis * 4, 4), 4)
            for address, value, size in mutations(self.mode):
                self.put(address, value, size)
            result = 0xA5000002
        else:
            assert target in (CALLBACK, NEGATIVE_CALLBACK), hex(target)
            self.put(OWNER + 0x47, target == NEGATIVE_CALLBACK, 1)
            result = self.callback_result
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result & 0xFFFFFFFF


class ConnectedPositionOracle(PositionOracle):
    def record_call(self, target):
        if target == self.symbols['func_15143134']:
            self.input_args, self.mutate = tuple(self.r[4:7]), False
            PositionOracle.record_call(self, target)
        elif target in (point.CONVERT, point.TRANSFORM, point.TRANSLATE):
            PointOracle.record_call(self, target)
        else:
            PositionOracle.record_call(self, target)

    def hook(self, target):
        if target in (point.CONVERT, point.TRANSFORM, point.TRANSLATE):
            PointOracle.hook(self, target)
        else:
            PositionOracle.hook(self, target)


class ConnectedUpdateOracle(callback_update.CallbackOracle):
    def record_call(self, target):
        if target == screen.ENTRY:
            self.calls.append((target, (self.r[4],)))
            self.events.append(('CALL', target, (self.r[4],)))
        elif target == screen.SYMBOLS['func_15143134']:
            self.input_args, self.mutate = tuple(self.r[4:7]), False
            self.calls.append((target, self.input_args))
            self.events.append(('CALL', target, self.input_args))
        elif target in (point.CONVERT, point.TRANSFORM, point.TRANSLATE):
            PointOracle.record_call(self, target)
        else:
            super().record_call(target)

    def hook(self, target):
        if target in (point.CONVERT, point.TRANSFORM, point.TRANSLATE):
            PointOracle.hook(self, target)
        else:
            super().hook(target)


class GameRecordActorPositionMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-actor-position-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>88I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline_path = cls.out / 'baseline.json'
        if not baseline_path.exists():
            original, _ = source_shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == original
            elf = cls.root / 'conker/build/conker.us.elf'
            functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
            slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
                struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
            previous = json.loads((cls.root / 'conker/build/game-record-callback-update-test/after.json').read_text())
            assert slots == previous['slots'] and len(slots) == 6058
            assert hashlib.sha256(elf.read_bytes()).hexdigest() == 'f240ca73721dfd7a24c0a85fd5697d45ea1ebc724a11ebd76d965e6b3cd86e99'
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            assert guards == previous['guards'] and len(guards) == 11469
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert len(progress) == 6044
            baseline_path.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            (cls.out / 'before-manifest.csv').write_bytes((cls.root / 'conker/retail_word_patches.us.csv').read_bytes())

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=0, result=0x87654321, phase=0, raw=True):
        ref = PositionReference(memory, mode, result)
        complete = outcome(ref)
        models = [PositionOracle(body, memory, mode, result, phase)
            for body in ((self.words, self.retail, self.raw) if raw else (self.words, self.retail))]
        for model in models:
            self.assertEqual(outcome(model), complete)
            self.assertEqual((external(model.memory), public(model.events), model.calls),
                (external(ref.memory), ref.events, ref.calls))
            if complete:
                self.assertEqual(model.r[2], ref.result)
        self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
            (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models[0], complete

    def test_01_complete_slot_frame_mapping_relocations_and_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (88, 56, 6))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes'], self.words), ('', 0, self.retail))
        expected_rel = {0xA0: [('R_MIPS_HI16', 'D_800AB280')], 0xA8: [('R_MIPS_LO16', 'D_800AB280')],
            0xC8: [('R_MIPS_HI16', 'D_800AB2D4')], 0xD4: [('R_MIPS_LO16', 'D_800AB2D4')],
            0xFC: [('R_MIPS_26', 'func_15143134')], 0x118: [('R_MIPS_HI16', 'D_8008FCA8')],
            0x134: [('R_MIPS_LO16', 'D_8008FCA8')]}
        self.assertEqual(self.meta['relocations'], expected_rel)
        self.assertTrue(all(self.raw[o // 4] == self.words[o // 4] for o in expected_rel))
        stack = {i * 4: (w >> 26, w >> 16 & 31, w & 65535)
            for i, w in enumerate(self.raw) if w >> 21 & 31 == 29}
        self.assertEqual(stack, {0: (9, 29, 0xFFC8), 4: (43, 31, 0x14), 0xF4: (43, 3, 0x18),
            0xF8: (43, 8, 0x1C), 0x100: (43, 7, 0x38), 0x104: (35, 3, 0x18),
            0x108: (35, 8, 0x1C), 0x10C: (35, 7, 0x38), 0x148: (35, 31, 0x14),
            0x150: (35, 31, 0x14), 0x154: (9, 29, 0x38)})
        for index in range(88):
            stale = list(self.raw)
            stale[index] ^= 0x80000000
            with self.assertRaisesRegex(ValueError, 'stale'):
                screen.normalize(stale)
        with self.assertRaisesRegex(ValueError, 'extent'):
            screen.normalize(self.raw[:-1])
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0]
            for p in screen.PROFILES]
        self.receipt('slot', dict(words=88, raw_frame=56, retail_frame=48, raw_differences=6,
            guards=6, relocation_uses=7, stack_uses=stack, stale_source_controls=88, profiles=profiles))

    def test_02_complete_entry_unsigned_joint_signed_callback_live_mutations(self):
        coverage, count = set(), 0
        cases = itertools.chain(
            ((j, c, f, g, m, r, p) for j, c, f, g, m, r, p in itertools.product(
                (0, 128, 255), (0, 127, 128, 254, 255), (0, 1, 128, 254, 255),
                range(8), (0, 1, 2, 3, 4, 5), (0, 0x80000000), (0, 8))),
            ((j, 255, 0xFE, 0, 0, 1, 0) for j in range(256)),
            ((0, c, 0xFE, 0, 0, 0xFFFFFFFF, 0) for c in range(256)))
        for joint, callback, flag, gate, mode, result, phase in cases:
            model, complete = self.compare(fixture(joint, callback, flag, gate), mode, result, phase)
            self.assertTrue(complete)
            coverage |= model.visits
            count += 1
        # Three compiler-generated unconditional pre-likely duplicate loads are unreachable.
        unreachable = {screen.ENTRY + o for o in (0x38, 0x5C, 0x98)}
        self.assertEqual(set(range(screen.ENTRY, screen.ENTRY + 352, 4)) - coverage, unreachable)
        self.receipt('guest', dict(cases=count, executions=count * 3,
            covered_words=88 - len(unreachable), unreachable_offsets=[hex(a - screen.ENTRY) for a in sorted(unreachable)],
            all_unsigned_joints=True, all_signed_callback_bytes=True, fabricated_valid_tables=True,
            strict_public_order=True, saved_registers=True, callback_return_propagation=True))

    def test_03_lazy_reads_fault_prefixes_and_table_owner_aliases(self):
        count = 0
        for gate, callback, mode in itertools.product(range(8), (128, 255), (0, 1, 3)):
            memory = fixture(callback=callback, gate=gate)
            ref = PositionReference(memory, mode).run()
            for address in sorted({e[1] + i for e in ref.events if e[0] in ('R', 'W') for i in range(e[2])}):
                missing = dict(memory)
                del missing[address]
                self.compare(missing, mode)
                count += 1
            lazy = {a: b for a, b in memory.items() if STACK - 0x600 <= a < STACK + 0x140 or
                any(e[0] in ('R', 'W') and e[1] <= a < e[1] + e[2] for e in ref.events)}
            self.compare(lazy, mode)
        aliases = 0
        for name, field, gate in (('D_8008FCA8', 0x2C, 0), ('D_800AB2D4', 0x46, 0),
                ('D_800AB2D4', 0x2D, 0), ('D_800AB280', 0x30, 0)):
            symbols = dict(screen.SYMBOLS, **{name: OWNER + field})
            meta, _ = screen.compile_candidate(self.root, self.out, 'alias-' + name + '-' + str(field))
            obj, elf = self.out / ('alias-' + name + '-' + str(field) + '.o'), self.out / ('alias-%s-%d.elf' % (name, field))
            script = self.out / 'alias.ld'
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % screen.ENTRY)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % i for i in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>88I', sections(elf)['.text'][1]))
            for callback, mode in itertools.product((128, 255), (0, 1, 2, 3)):
                memory = fixture(callback=callback, gate=gate, symbols=symbols)
                # The selected indirect target must remain a callable value under the alias.
                for i in (-128, -1, 0):
                    put(memory, symbols['D_8008FCA8'] + i * 4, NEGATIVE_CALLBACK if i < 0 else CALLBACK)
                ref = PositionReference(memory, mode, symbols=symbols)
                done = outcome(ref)
                for body in (words, screen.normalize(words)):
                    model = PositionOracle(body, memory, mode, symbols=symbols)
                    self.assertEqual(outcome(model), done)
                    self.assertEqual((external(model.memory), public(model.events), model.calls),
                        (external(ref.memory), ref.events, ref.calls))
                aliases += 1
        self.receipt('faults', dict(missing_byte_pairs=count, table_owner_alias_cases=aliases,
            hardware_fault_state=False, portable_invalid_pointer_semantics=False))

    def test_04_complete_forms_and_effective_negative_controls(self):
        records, negatives, different_prefixes = [], [], []
        samples = [(fixture(j, c, 0xFE, g), m, r) for j, c, g, m, r in itertools.product(
            (0, 128), (128, 255), (0, 1, 3, 4, 7), (0, 1, 2, 3), (0, 0x87654321))]
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            records.append(meta)
            same, prefixes = [], []
            for memory, mode, result in samples:
                ref = PositionReference(memory, mode, result).run()
                model = PositionOracle(words, memory, mode, result)
                complete = outcome(model)
                same.append(complete and (external(model.memory), model.calls, model.r[2]) ==
                    (external(ref.memory), ref.calls, ref.result))
                prefixes.append(public(model.events) == ref.events)
            if name.startswith('negative-'):
                self.assertFalse(all(same), name)
                negatives.append(name)
            else:
                self.assertTrue(all(same), name)
                if not all(prefixes):
                    different_prefixes.append(name)
        self.receipt('forms', dict(forms=len(records), samples=len(samples),
            effective_compiled_negatives=negatives, exploratory_public_prefix_changes=different_prefixes, measurements=records))

    def test_05_copied_owner_actual_padder_and_independent_relocations(self):
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
        copied = list(struct.unpack_from('>88I', text, current[screen.FUNCTION]['value']))
        guards = screen.owner_guards(copied)
        self.assertEqual(len(guards), 6)
        baseline = json.loads((self.out / 'baseline.json').read_text())
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[:11469], baseline['guards'])
        self.assertIn(rows[11469:], ([], guards))
        manifest = self.out / 'proposed.csv'
        def emit(suffix):
            with manifest.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows[:11469] + suffix)
            return emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
                word_patches_path=manifest, filename='generated_204660')
        for index in range(6):
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
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 352)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        cases = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            defs = dict(screen.SYMBOLS)
            for i, name in enumerate(('D_800AB280', 'D_800AB2D4', 'D_8008FCA8')):
                if variant:
                    defs[name] = (0x70007FFC, 0x70108000, 0x7020FFF8)[variant - 1] + i * 0x10000
            if variant:
                defs['func_15143134'] = (entry & 0xF0000000) + 0x100800
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = self.out / ('rebase-%d.elf' % variant)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            body = list(struct.unpack_from('>88I', sections(elf)['.text'][1]))
            for joint, callback, mode in itertools.product((0, 128, 255), (128, 255), (0, 1, 2, 3)):
                memory = fixture(joint, callback, symbols=defs)
                ref = PositionReference(memory, mode, symbols=defs).run()
                model = PositionOracle(body, memory, mode, entry=entry, symbols=defs).run()
                self.assertEqual((external(model.memory), public(model.events), model.calls, model.r[2]),
                    (external(ref.memory), ref.events, ref.calls, ref.result))
                cases += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=len(diagnostics[0]),
            pools_and_relative_relocations_unchanged=True, guards=6, stale_guards=6,
            padded_bytes=352, independent_links=4, cases=cases))

    def test_06_linked_baseline_or_installed_closure(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(hashlib.sha256(elf.read_bytes()).hexdigest(), baseline['elf_sha256'])
        self.assertEqual(elf.read_bytes(), (self.out / 'before.elf').read_bytes())
        self.assertTrue((self.root / 'conker/retail_word_patches.us.csv').read_bytes().startswith(
            (self.out / 'before-manifest.csv').read_bytes()))
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        self.assertEqual({n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}, baseline['slots'])
        self.assertEqual(functions[screen.FUNCTION], self.retail)
        old, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == selected
        with (self.root / 'conker/progress.csv').open(newline='') as stream:
            progress = list(csv.DictReader(stream))
        self.assertEqual(progress, [dict(r, language='c') if installed and r['function'] == screen.FUNCTION else r
            for r in baseline['progress']])
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        self.assertEqual(guards, baseline['guards'] + (screen.owner_guards(self.raw) if installed else []))
        totals = {}
        for section in ('total', 'init', 'game', 'debugger'):
            rows = [r for r in progress if r['language'] in ('c', 'asm') and (section == 'total' or r['section'] == section)]
            converted = [r for r in rows if r['language'] == 'c']
            totals[section] = dict(converted=len(converted), functions=len(rows),
                converted_percent=100 * len(converted) / len(rows),
                converted_bytes=sum(int(r['length']) for r in converted), bytes=sum(int(r['length']) for r in rows),
                byte_percent=100 * sum(int(r['length']) for r in converted) / sum(int(r['length']) for r in rows))
        self.receipt('linked', dict(installed=installed, symbols=len(functions), complete_ELF_unchanged=True,
            guards=len(guards), target_words=88, differences=0, totals=totals))
        if installed:
            self.receipt('after', dict(slots=baseline['slots'], guards=guards, progress=progress))

    def test_07_actual_native32_unsigned_joint_signed_callback_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8; typedef signed char s8; typedef int s32;
typedef unsigned int u32; typedef float f32;
#define NULL ((void *)0)
static union { u32 align; u8 b[512]; } ownerStorage, secondaryStorage;
static union { u32 align; u8 b[1024]; } actorStorage;
static u8 *owner=ownerStorage.b, *actor=actorStorage.b, *secondary=secondaryStorage.b;
static f32 D_800AB280[256][3]; static u8 D_800AB2D4[256];
static u8 matrices[256*64];
static s32 (*callbacks[512])(u8 *);
#define D_8008FCA8 (callbacks+128)
static int transforms, calls, error, mode; static s32 returned;
static int expectedJoint, expectedSigned;
static s32 secondaryCall(u8 *p) {
    if(p!=owner) error=1;
    if(expectedSigned<0) error=2;
    calls++; p[0x47]=0x5A; return returned;
}
static s32 negativeCall(u8 *p) {
    if(p!=owner || expectedSigned>=0) error=2;
    calls++; p[0x47]=0x5B; return returned;
}
static void func_15143134(f32 *input,f32 *output,u8 *matrix) {
    if(input!=D_800AB280[expectedJoint] || output!=(f32 *)(owner+0x30)
       || matrix!=matrices+D_800AB2D4[expectedJoint]*64) error=3;
    transforms++; output[0]=input[0]; output[1]=input[1]; output[2]=input[2];
    if(mode==1) owner[0x2D]=0xFE;
    if(mode==2) owner[0x46]=255;
    if(mode==3) owner[0x46]=128;
}
static void initialize(int flag,int joint,int byte,int gate,int mutate) {
    int i;
    for(i=0;i<512;i++) { owner[i]=0xA5; secondary[i]=0xA5; callbacks[i]=i<128?negativeCall:secondaryCall; }
    for(i=0;i<1024;i++) actor[i]=0xA5;
    for(i=0;i<256;i++) { D_800AB280[i][0]=(f32)i; D_800AB280[i][1]=-(f32)i;
        D_800AB280[i][2]=0.5f; D_800AB2D4[i]=(u8)(i*3+1); }
    *(u8 **)(owner+0x40)=actor; owner[0x44]=7; owner[0x45]=(u8)joint;
    owner[0x46]=(u8)byte; owner[0x2D]=(u8)flag;
    *(s32 *)actor=gate==1?0:1; actor[0x3B]=(u8)(gate==2?8:7);
    *(u8 **)(actor+0x1D4)=gate==3?NULL:matrices;
    *(u8 **)(actor+0x31C)=gate>=4&&gate<=6?secondary:NULL;
    secondary[0x197]=(u8)(gate==5?0:1); *(u8 **)(actor+0x318)=gate==6?NULL:actor;
    actor[7]=(u8)(gate==7?0:255);
    transforms=calls=error=0; mode=mutate; expectedJoint=joint;
    expectedSigned=(s8)(mutate==2?255:mutate==3?128:byte);
}
''' + screen.SELECTED + '\n'
        self.run_host(r'''
int flag,joint,byte,gate,mutate,i; s32 answer;
u8 before[512]; u8 expectedFlag;
for(flag=0;flag<256;flag++) for(joint=0;joint<256;joint++) {
    initialize(flag,joint,255,0,0);
    for(i=0;i<512;i++) before[i]=owner[i];
    answer=func_151D75C4(owner);
    if(answer!=1 || error || transforms!=1 || calls || owner[0x2D]!=(u8)(flag|1)) return 1;
    if(*(f32 *)(owner+0x30)!=(f32)joint || *(f32 *)(owner+0x34)!=-(f32)joint || *(f32 *)(owner+0x38)!=0.5f) return 2;
    for(i=0;i<512;i++) if(i!=0x2D && !(i>=0x30&&i<0x3C) && owner[i]!=before[i]) return 3;
}
for(byte=0;byte<256;byte++) for(gate=0;gate<8;gate++) for(mutate=0;mutate<4;mutate++) {
    initialize(0xFE,128,byte,gate,mutate); returned=(s32)0x87654321;
    for(i=0;i<512;i++) before[i]=owner[i];
    answer=func_151D75C4(owner);
    if(error) return 4;
    if(gate==1 || gate==2) {
        if(answer || transforms || calls || owner[0x2D]!=0xFE) return 5;
    } else if(gate==3 || gate==4 || gate==7) {
        if(answer!=1 || transforms || calls || owner[0x2D]!=0xFE) return 6;
    } else {
        expectedFlag=(u8)(mutate==1?255:0xFE|1);
        if(transforms!=1 || owner[0x2D]!=expectedFlag || calls!=(expectedSigned!=-1)
            || answer!=(expectedSigned==-1?1:returned)) return 7;
    }
    for(i=0;i<512;i++) if(i!=0x2D && i!=0x46 && i!=0x47 && !(i>=0x30&&i<0x3C) && owner[i]!=before[i]) return 8;
}
''')
        self.receipt('native', dict(cases=65536 + 256 * 8 * 4, all_flag_joint_pairs=True,
            all_signed_callback_bytes=True, full_512_byte_canaries=True,
            actual_native32_C=True, transform_and_callback_bounded=True))

    def test_08_complete_point_helper_with_real_joint_tables(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(len(functions['func_15143134']), 98)
        pool_address, pool = sections(self.root / 'conker/build/conker.us.elf')['.game_data']
        points = pool[0x800AB280 - pool_address:0x800AB2D4 - pool_address]
        mapping = pool[0x800AB2D4 - pool_address:0x800AB2DC - pool_address]
        self.assertEqual((len(points), mapping.hex()), (84, '0f110f0206060e00'))
        connected = dict(zip(range(0x15143134, 0x15143134 + 392, 4), functions['func_15143134']))
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        for address, offset, length in ((point.CONVERT, 0x21D368, 46),
                (point.TRANSFORM, 0xD4E10, 40), (point.TRANSLATE, 0x16F7C4, 49),
                (0x150A7A14, 0xD4EC4, 13)):
            connected.update(zip(range(address, address + length * 4, 4), struct.unpack_from('>%dI' % length, rom, offset)))
        count, seen = 0, set()
        for joint, flag, phase, secondary_byte in itertools.product(range(7), (0, 1), (0, 8), (128, 255)):
            memory = fixture(joint, secondary_byte)
            memory.update({0x800AB280 + i: b for i, b in enumerate(points)})
            memory.update({0x800AB2D4 + i: b for i, b in enumerate(mapping)})
            memory.update({STATUS + i: 0 for i in range(32)})
            put(memory, FLAG, flag, 1)
            values = [0.] * 16
            for i in (0, 5, 10, 15): values[i] = 0.5
            values[12:15] = [3., -4., 5.]
            if flag:
                integers = [int(v * 65536) & 0xFFFFFFFF for v in values]
                payload = struct.pack('>32H', *[v >> 16 for v in integers], *[v & 65535 for v in integers])
            else:
                payload = struct.pack('>16f', *values)
            matrix = MATRICES + mapping[joint] * 64
            memory.update({matrix + i: b for i, b in enumerate(payload)})
            models = [ConnectedPositionOracle(body, memory, phase=phase, connected=connected).run()
                for body in (self.raw, self.words, self.retail)]
            expected = tuple(bits(v * 0.5 + t) for v, t in zip(struct.unpack_from('>3f', points, joint * 12), (3., -4., 5.)))
            for model in models:
                self.assertEqual(tuple(read(model.memory, OWNER + 0x30 + i * 4) for i in range(3)), expected)
                self.assertEqual(model.r[2], 1 if secondary_byte == 255 else 0x87654321)
                seen.update(model.visits)
            def canonical(value):
                if isinstance(value, tuple):
                    return tuple(canonical(item) for item in value)
                return value + 8 if isinstance(value, int) and STACK - 0x600 <= value < STACK else value
            raw_events = tuple(canonical(e) if e[0] == 'CALL' else e for e in public(models[0].events))
            self.assertEqual((external(models[0].memory), raw_events, canonical(tuple(models[0].calls))),
                (external(models[2].memory), tuple(public(models[2].events)), tuple(models[2].calls)))
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events),
                (models[2].r, models[2].f, models[2].memory, models[2].events))
            count += 1
        self.assertTrue(set(range(point.CONVERT, point.CONVERT + 180, 4)) <= seen)
        self.receipt('connected', dict(cases=count, executions=count * 3, actual_joint_table_entries=7,
            point_words=98, sdk_words=46, sdk_executed_words=45, matrix_words=40, translation_words=49,
            all_45_sdk_words_reached=True, secondary_callback_bounded=True, hardware_gameplay=False))

    def test_09_effective_partial_frame_mapping_negatives(self):
        failures = []
        for guard in screen.owner_guards(self.raw):
            offset = int(guard['offset'], 0)
            changed = list(self.words)
            changed[offset // 4] = self.raw[offset // 4]
            model = PositionOracle(changed, fixture(callback=128))
            try:
                model.run()
            except AssertionError as error:
                self.assertTrue(isinstance(error.args[0], tuple) and error.args[0][0] in
                    ('unmapped read', 'unmapped store', 'saved register'), error)
                failures.append(dict(offset=offset, witness=error.args[0][0]))
            else:
                expected = PositionOracle(self.words, fixture(callback=128)).run()
                self.assertNotEqual((model.memory, model.calls), (expected.memory, expected.calls))
                if offset == 0x100:
                    self.assertNotEqual(read(model.memory, STACK + 8), read(expected.memory, STACK + 8))
                failures.append(dict(offset=offset, witness='changed caller home or callback arguments'))
        self.receipt('partial-negatives', dict(witnesses=failures, no_budget_or_unsupported_opcode=True))

    def test_10_actual_slot_zero_caller_capture_distance_and_clear(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        pool_address, pool = sections(self.root / 'conker/build/conker.us.elf')['.game_data']
        table = callback_update.screen.SYMBOLS['D_8008FCA0']
        self.assertEqual(struct.unpack_from('>I', pool, table - pool_address)[0], screen.ENTRY)
        selected = ('func_15143134', 'func_15143E64', 'func_151D77C8')
        self.assertEqual([len(functions[n]) for n in selected], [98, 12, 26])
        connected = {addresses[n] + i * 4: w for n in selected for i, w in enumerate(functions[n])}
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        for address, offset, length in ((point.CONVERT, 0x21D368, 46),
                (point.TRANSFORM, 0xD4E10, 40), (point.TRANSLATE, 0x16F7C4, 49),
                (0x150A7A14, 0xD4EC4, 13)):
            connected.update(zip(range(address, address + length * 4, 4), struct.unpack_from('>%dI' % length, rom, offset)))
        points = pool[0x800AB280 - pool_address:0x800AB2D4 - pool_address]
        mapping = pool[0x800AB2D4 - pool_address:0x800AB2DC - pool_address]
        count = 0
        for joint, prior_flag, secondary_byte, result, gate, phase in itertools.product(
                (0, 6), (0, 1), (128, 255), (0, 1), (0, 1, 3, 4, 7), (0, 8)):
            memory = fixture(joint, secondary_byte, prior_flag, gate)
            memory.update({0x800AB280 + i: b for i, b in enumerate(points)})
            memory.update({0x800AB2D4 + i: b for i, b in enumerate(mapping)})
            attached, nested = 0x25000, 0x26000
            for base in (attached, nested):
                memory.update({base + i: 0 for i in range(0xC0)})
            memory.update({STATUS + i: 0 for i in range(32)})
            put(memory, FLAG, 0, 1)
            matrix = MATRICES + mapping[joint] * 64
            values = [0.] * 16
            for i in (0, 5, 10, 15): values[i] = 0.5
            values[12:15] = [3., -4., 5.]
            memory.update({matrix + i: b for i, b in enumerate(struct.pack('>16f', *values))})
            for address, value, size in ((OWNER + 0x28, attached, 4), (OWNER + 0x2C, 0, 1),
                    (OWNER + 0x3C, bits(-1.), 4), (table, screen.ENTRY, 4),
                    (attached + 0x98, nested, 4), (attached + 0x1E, 0xFFFF, 2), (nested, 0x12345678, 4)):
                put(memory, address, value, size)
            models = []
            for body in (self.raw, self.words, self.retail):
                code = dict(connected)
                code.update(zip(range(screen.ENTRY, screen.ENTRY + 352, 4), body))
                models.append(ConnectedUpdateOracle(functions['func_151D7264'], memory, result=result,
                    phase=phase, connected=code).run())
            # Shrinking this callback's frame translates nested scratch pointers by exactly eight.
            def canonical(value):
                if isinstance(value, tuple):
                    return tuple(canonical(item) for item in value)
                return value + 8 if isinstance(value, int) and STACK - 0x600 <= value < STACK else value
            raw_events = tuple(canonical(e) if e[0] == 'CALL' else e for e in public(models[0].events))
            self.assertEqual((external(models[0].memory), raw_events, canonical(tuple(models[0].calls))),
                (external(models[2].memory), tuple(public(models[2].events)), tuple(models[2].calls)))
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events),
                (models[2].r, models[2].f, models[2].memory, models[2].events))
            for model in models:
                failed = gate == 1 or (gate == 0 and secondary_byte == 128 and not result)
                if failed:
                    self.assertEqual(read(model.memory, OWNER + 0xE, 2), 0xFFFF)
                else:
                    self.assertEqual((read(model.memory, OWNER + 0x28), read(model.memory, nested)), (0, 0))
                    self.assertEqual(read(model.memory, attached + 0x1E, 2), 0xFFFD)
                    self.assertEqual(read(model.memory, attached + 0x1C, 2), 20)
            count += 1
        self.receipt('caller', dict(cases=count, executions=count * 3, actual_table_slot=0,
            complete_caller_words=81, complete_callback_words=88, point_words=98,
            distance_words=12, clear_words=26, secondary_callback_bounded=True, hardware_gameplay=False))
