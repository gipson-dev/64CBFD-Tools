"""Live ring cursor, unsigned wrap count, final aliases and consumed callback result."""

import csv
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_ring_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_random_curve_record as native
from tools.tests import test_game_record_velocity_match as velocity
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.game_animation_timeline_oracle import bits, signed

SOURCE = 'conker/src/game/generated_204660.c'
OWNER, RECORDS, ALTERNATE = 0x20000, 0x24000, 0x28000
DISPATCHER, RELEASE, TABLE = 0x15147740, 0x1516972C, 0x8008A200
XYZ = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0xBF800000,
       0x7F7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0xFFC12345)
INSERT = screen.DECLARATIONS + '\ns32 func_151D792C(u8 *owner);\n\n'
INSERT = INSERT.replace('typedef struct {\n    RingPosition151D792C position;\n    f32 velocity;\n    u8 remaining[12];\n} RingRecord151D792C;\n\n', '')


def source_shapes(root):
    source = (root / SOURCE).read_text()
    baseline = source.replace(screen.SELECTED, screen.ORIGINAL)
    assert baseline.count(screen.ORIGINAL) == 1
    if INSERT in baseline:
        selected = baseline.replace(screen.ORIGINAL, screen.SELECTED)
        # Other converted callers still need the shared clock and integrator declarations.
        baseline = baseline.replace(INSERT, 'extern f32 D_800BE9A4;\nvoid func_151D8718(f32 *, f32 *, f32);\n\n')
    else:
        selected = baseline.replace('#include <ultra64.h>\n\n', '#include <ultra64.h>\n\n' + INSERT, 1).replace(screen.ORIGINAL, screen.SELECTED)
    return baseline, selected


def public(address):
    return not STACK - 0x300 <= address < STACK + 0x100


def public_memory(model):
    return {a: v for a, v in model.memory.items() if public(a)}


def public_events(model):
    return [e for e in model.events if e[0] == 'CALL' or public(e[1])]


def byte_signed(value):
    return value if value < 128 else value - 256


def fixture(state=2, current=1, goal=2, count=4, flags=0, pattern=0, layout=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: 0xA5 for i in range(-0x300, 0x100)}
    memory.update({OWNER + i: (i * 17 + 0xA5) & 255 for i in range(-16, 0xB0)})
    indices = set(range(max(8, byte_signed(current) + 1))) | {-1, byte_signed(goal), 127, 255}
    if count >= 128:
        indices.update(range(count))
    for base in (RECORDS, ALTERNATE):
        for index in indices:
            for offset in range(28):
                memory[base + index * 28 + offset] = (offset * 17 + index + 0xA5) & 255
            for field in range(4):
                value = bits(float(index + field + 1)) if pattern == 0 else XYZ[(pattern + index + field) % len(XYZ)]
                put(memory, base + index * 28 + field * 4, value)
    records = RECORDS if not layout else OWNER + (0x54 if layout == 1 else 0x50)
    for address, value, width in ((OWNER + 0x2C, state & 255, 1), (OWNER + 0x2D, goal & 255, 1),
            (OWNER + 0x2E, current & 255, 1), (OWNER + 0x25, count, 1),
            (OWNER + 0x1E, flags, 2), (OWNER + 0x94, records, 4), (symbols['D_800BE9A4'], 0x3F800000, 4)):
        put(memory, address, value, width)
    for address, value in ((velocity.screen.SYMBOLS['D_800AB2EC'], 0x3E6F9DB3),
                           (velocity.screen.SYMBOLS['D_800AB2F0'], 0x3DEF9DB3)):
        put(memory, address, value)
    return memory


def actions(mode, index, symbols):
    if index:
        return []
    return {0: [], 1: [(OWNER + 0x2D, 0, 1)], 2: [(OWNER + 0x2C, 0, 1)],
        3: [(OWNER + 0x94, ALTERNATE, 4)], 4: [(symbols['D_800BE9A4'], 0xBF800000, 4)],
        5: [(OWNER + 0x25, 3, 1), (OWNER + 0x2D, 2, 1)],
        6: [(OWNER + 0x2D, 0, 1), (OWNER + 0x2C, 255, 1), (OWNER + 0x94, ALTERNATE, 4)]}[mode]


class RingReference:
    def __init__(self, memory, mode=0, symbols=None, actual=False):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.mode, self.symbols, self.actual = mode, symbols or screen.SYMBOLS, actual

    def get(self, address, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned read', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned store', address, size)
        self.events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def call(self, position, delta):
        args = (position, (position + 12) & 0xFFFFFFFF, delta)
        index = len(self.calls)
        self.calls.append(args)
        self.events.append(('CALL', self.symbols['func_151D8718'], args))
        if self.actual:
            self.memory, events = velocity.reference(self.memory, args[0], args[1], delta)
            self.events.extend(events)
        else:
            height, old = self.get(position + 4), self.get(args[1])
            self.put(position + 4, height ^ delta)
            self.put(args[1], old ^ 0x01010101)
        for address, value, width in actions(self.mode, index, self.symbols):
            self.put(address, value, width)

    def run(self):
        state = byte_signed(self.get(OWNER + 0x2C, 1))
        records = self.get(OWNER + 0x94)
        if state < 2 and self.get(OWNER + 0x1E, 2) & 8:
            self.result = 0
            return self
        cursor = byte_signed(self.get(OWNER + 0x2E, 1))
        goal = byte_signed(self.get(OWNER + 0x2D, 1))
        if cursor != goal:
            for _ in range(512):
                cursor -= 1
                if cursor < 0:
                    cursor = self.get(OWNER + 0x25, 1) - 1
                self.call((records + cursor * 28) & 0xFFFFFFFF, self.get(self.symbols['D_800BE9A4']))
                goal = byte_signed(self.get(OWNER + 0x2D, 1))
                if cursor == goal:
                    break
            else:
                raise AssertionError('reference domain does not terminate')
            state = byte_signed(self.get(OWNER + 0x2C, 1))
        if state > 0:
            source = (records + goal * 28) & 0xFFFFFFFF
            for field in range(3):
                self.put(OWNER + 0x54 + field * 4, self.get(source + field * 4))
        else:
            for field in range(3):
                self.put(OWNER + 0x54 + field * 4, 0)
        self.result = 1
        return self


class RingOracle(velocity.CallerOracle):
    def __init__(self, words, memory, mode=0, phase=0, entry=screen.ENTRY, symbols=None, connected=None):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(OWNER,), connected=connected)
        self.mode, self.symbols = mode, symbols or screen.SYMBOLS
        self.releases, self.callbacks = [], []

    def get(self, address, size):
        assert address % size == 0, ('unaligned read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        assert address % size == 0, ('unaligned store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        if target == screen.ENTRY:
            self.callbacks.append(self.r[4])
        elif target == RELEASE:
            self.releases.append(self.r[4])
        else:
            assert target == self.symbols['func_151D8718']
            args = tuple(self.r[4:7])
            self.calls.append(args)
            self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == RELEASE:
            result = 0xA5000002
        else:
            assert target == self.symbols['func_151D8718']
            position, speed, delta = self.calls[-1]
            height, old = self.get(position + 4, 4), self.get(speed, 4)
            self.put(position + 4, height ^ delta, 4)
            self.put(speed, old ^ 0x01010101, 4)
            for address, value, width in actions(self.mode if self.mode != 7 else 0, len(self.calls) - 1, self.symbols):
                self.put(address, value, width)
            if self.mode == 7:
                for i in range(4):
                    self.put(self.r[29] + i * 4, ALTERNATE + i, 4)
            result = 0xA5000002
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


def outcome(model):
    try:
        model.run()
        return True
    except AssertionError as error:
        assert error.args and isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return False


class GameRecordRingUpdateTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-update-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>67I', cls.rom, screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None):
        ref = RingReference(memory, mode if mode != 7 else 0, symbols)
        completed = outcome(ref)
        models = []
        for body in (self.words if words is None else words, self.retail):
            model = RingOracle(body, memory, mode, phase, entry, symbols)
            self.assertEqual(outcome(model), completed)
            self.assertEqual((public_memory(model), public_events(model), model.calls),
                             (public_memory(ref), ref.events, ref.calls))
            if completed:
                self.assertEqual(model.r[2], ref.result)
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                             (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models[0], completed

    def test_01_complete_slot_profiles_and_closed_stale_guards(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (67, 0x30, 13))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.record['relocations'], {0x54: [('R_MIPS_HI16', 'D_800BE9A4')],
            0x58: [('R_MIPS_LO16', 'D_800BE9A4')], 0x88: [('R_MIPS_26', 'func_151D8718')]})
        for index in (0, *range(0xA0 // 4, 0xD4 // 4)):
            stale = self.raw.copy()
            stale[index] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in ('o2g3', 'o2', 'o1g3', 'o1')]
        self.assertEqual([(m['body_words'], m['frame'], m['differences']) for m in profiles],
            [(67, 0x30, 13), (66, 0x30, 38), (79, 0x28, 78), (78, 0x28, 77)])
        self.receipt('slot', dict(words=67, bytes=268, frame=0x30, direct_words=54, guards=13,
            guard_offsets=list(range(0xA0, 0xD4, 4)), no_insert_omit_or_relocation_changes=True, profiles=profiles))

    def test_02_signed_bytes_wrap_live_calls_aliases_and_reachable_words(self):
        count, seen = 0, set()
        for state, current, goal, flags, mode, phase in itertools.product((128, 255, 0, 1, 2, 127), range(4), range(4), (0, 8), range(5), (0, 8)):
            model, completed = self.compare(fixture(state, current, goal, flags=flags), mode, phase)
            self.assertTrue(completed)
            seen.update(model.visits)
            count += 1
        for byte in range(256):
            for memory in (fixture(state=byte, current=1, goal=1, pattern=1),
                           fixture(current=byte, goal=0, pattern=1), fixture(current=byte, goal=byte, pattern=1)):
                self.assertTrue(self.compare(memory, phase=(byte & 1) * 8)[1])
                count += 1
        for wrap in (0, 1, 127, 128, 255):
            memory = fixture(current=0, goal=255 if wrap == 0 else wrap - 1 if wrap <= 128 else 127, count=wrap)
            self.assertTrue(self.compare(memory)[1])
            count += 1
        for mode, phase in itertools.product((5, 6, 7), (0, 8)):
            self.assertTrue(self.compare(fixture(current=1, goal=2), mode, phase)[1])
            count += 1
        for layout, pattern, phase in itertools.product((1, 2), range(len(XYZ)), (0, 8)):
            self.assertTrue(self.compare(fixture(current=0, goal=0, layout=layout, pattern=pattern), phase=phase)[1])
            count += 1
        unreachable = {screen.ENTRY + 0x4C, screen.ENTRY + 0xD4}
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 268, 4)) - unreachable)
        self.receipt('guest', dict(cases=count, all_256_state_current_goal_bytes=True, wrap_counts=[0, 1, 127, 128, 255],
            live_goal_state_count_delta_and_captured_buffer=True, forward_copy_aliases=True,
            full_retail_GP_FP_private_memory_and_trace=True, reachable_words=65, compiler_dead_words=2,
            partial_overlap_and_negative_guest_pointers_not_portable_C_claims=True))

    def test_03_lazy_gates_and_required_fault_prefixes(self):
        faults, lazy = 0, 0
        for state, flags, current, goal, phase in itertools.product((0, 2), (0, 8), (0,), (0,), (0, 8)):
            memory = fixture(state, current, goal, flags=flags)
            ref = RingReference(memory).run()
            required = {e[1] + i for e in ref.events if e[0] != 'CALL' for i in range(e[2])}
            trimmed = {a: v for a, v in memory.items() if not public(a) or a in required}
            self.assertTrue(self.compare(trimmed, phase=phase)[1])
            lazy += 1
        for mode, phase in itertools.product(range(5), (0, 8)):
            memory = fixture()
            ref = RingReference(memory, mode).run()
            for address, size in dict.fromkeys((e[1], e[2]) for e in ref.events if e[0] != 'CALL'):
                broken = dict(memory)
                del broken[address + size - 1]
                self.assertFalse(self.compare(broken, mode, phase)[1])
                faults += 1
        memory = fixture()
        put(memory, OWNER + 0x94, RECORDS + 1)
        self.assertFalse(self.compare(memory)[1])
        faults += 1
        self.receipt('faults', dict(cases=faults, lazy_cases=lazy, public_prefix_and_complete_retail_partial_state=True,
            unconditional_buffer_pointer_read_on_gate=True, hardware_exception_and_portable_C_faults_not_modeled=True))

    def test_04_actual_native32_flags_bytes_calls_and_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.DECLARATIONS + screen.SELECTED + NATIVE_CHECK
        self.run_host('unsigned flag,state,cur,goal,mode; static unsigned states[]={0,1,2,127,128,255};\n'
            'if(sizeof(void*)!=4)return 10;\n'
            'for(flag=0;flag<65536;flag++)for(state=0;state<6;state++)if(check(states[state],0,0,4,flag,0,512))return 11;\n'
            'for(cur=0;cur<256;cur++)for(state=0;state<6;state++)for(goal=0;goal<4;goal++)if(check(states[state],cur,goal,4,0,0,8192))return 12;\n'
            'for(state=0;state<256;state++)for(cur=0;cur<4;cur++)for(goal=0;goal<4;goal++)if(check(state,cur,goal,4,0,0,512))return 13;\n'
            'for(state=0;state<6;state++)for(cur=0;cur<4;cur++)for(goal=0;goal<4;goal++)for(mode=0;mode<7;mode++)if(check(states[state],cur,goal,4,0,mode,512))return 14;\n'
            'if(check(2,0,127,128,0,0,8192)||check(2,0,127,255,0,0,8192)||check(2,0,255,0,0,0,512))return 15;')
        self.receipt('native', dict(executions=65536 * 6 + 256 * 6 * 4 + 256 * 4 * 4 + 6 * 4 * 4 * 7 + 3,
            all_unsigned_flag_patterns=True, all_signed_state_current_bytes=True, actual_C_volatile_typed_call=True,
            independent_numeric_reference_calls_and_full_512_or_8192_byte_canaries=True,
            native_mixed_pointer_pointer_float_ABI=True, mutation_modes=7, prepared_valid_buffer_pointers=True))

    def test_05_complete_source_forms_and_effective_negatives(self):
        records, ordinary, negatives = [], 0, 0
        samples = [(fixture(state, 1, 2, flags=flag, pattern=1), mode)
            for state, flag, mode in itertools.product((0, 1, 2, 128), (0, 8, 4), range(5))]
        samples += [(fixture(current=255, goal=255, pattern=1), 0), (fixture(current=0, goal=127, count=128), 0)]
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            equal, traces = [], []
            for memory, mode in samples:
                ref = RingReference(memory, mode)
                expected = outcome(ref)
                model = RingOracle(words, memory, mode)
                complete = outcome(model)
                equal.append((complete, public_memory(model), model.calls,
                    model.r[2] if complete else None) == (expected, public_memory(ref), ref.calls,
                    ref.result if expected else None))
                traces.append(public_events(model) == ref.events)
            if name.startswith('negative-'):
                self.assertFalse(all(equal) and all(traces), name)
                negatives += 1
            else:
                self.assertTrue(all(equal), name)
                ordinary += len(equal)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary, effective_negatives=negatives, measurements=records))

    def test_06_copied_owner_real_padder_and_independent_links(self):
        objects, diagnostics = [], []
        for name, source in zip(('baseline', 'selected'), source_shapes(self.root)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            diagnostics.append(warnings)
            processed = self.out / ('owner-' + name + '-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            before = previous[name]
            if name != screen.FUNCTION:
                self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[before['value']:before['value'] + before['size']], name)
                self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                                 {o - before['value']: r for o, r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        target = current[screen.FUNCTION]
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(text[target['value']:target['value'] + 268], isolated[:268])
        self.assertEqual({o - target['value']: r for o, r in rel.items() if target['value'] <= o < target['value'] + 268}, isolated_rel)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        prefix, suffix = guards[:11155], guards[11168:]
        target_guards = screen.owner_guards()
        proposed = prefix + target_guards + suffix
        assert_guard_history(self, proposed)
        for bad in (prefix + target_guards[:-1] + suffix,
                    prefix + target_guards + [dict(target_guards[-1])] + suffix,
                    prefix + list(reversed(target_guards)) + suffix):
            with self.assertRaises(AssertionError):
                assert_guard_history(self, bad)
        manifest = self.out / 'proposed.csv'
        with manifest.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=guards[0].keys())
            writer.writeheader()
            writer.writerows(proposed)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s', word_patches_path=manifest, filename='generated_204660')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual((functions[screen.FUNCTION]['size'], relocations), (268, isolated_rel))
        executions = 0
        for index, (entry, clock) in enumerate(zip((screen.ENTRY, 0x10007FFC, 0x7FFF8000, 0x80000000, 0x8FFF7FFC, 0x1FFF8000),
                (0x7FFC, 0x8000, 0xFFF8, 0x80007FFC, 0x80008000, 0xFFFF8000))):
            symbols = {'D_800BE9A4': clock, 'func_151D8718': (entry & 0xF0000000) + 0x108004}
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>67I', sections(elf)['.text'][1]))
            expected = list(self.retail)
            expected[0x54 // 4] = 0x3C120000 | (((clock + 0x8000) >> 16) & 65535)
            expected[0x58 // 4] = 0x26520000 | (clock & 65535)
            expected[0x88 // 4] = 0x0C000000 | ((symbols['func_151D8718'] >> 2) & 0x3FFFFFF)
            self.assertEqual(words, expected)
            for state, mode, phase in itertools.product((0, 2, 128), (0, 1, 3, 4), (0, 8)):
                memory = fixture(state=state, symbols=symbols)
                ref = RingReference(memory, mode, symbols).run()
                model = RingOracle(words, memory, mode, phase, entry, symbols).run()
                self.assertEqual((public_memory(model), public_events(model), model.calls, model.r[2]),
                    (public_memory(ref), ref.events, ref.calls, ref.result))
                executions += 1
        self.receipt('owner-padder', dict(neighbors=len(current) - 1, unchanged_warning_count=len(diagnostics[0]),
            pools_and_relative_relocations_unchanged=True, padded_bytes=268, guards=13, independent_links=6,
            independently_expected_HI_LO_JAL_sites=3, executions=executions))

    def test_07_actual_integrator_and_consuming_full_dispatcher(self):
        _, raw = velocity.screen.compile_candidate(self.root, self.out, 'velocity')
        helper = velocity.screen.normalize(raw)
        self.assertEqual(helper, list(struct.unpack_from('>19I', self.rom, velocity.screen.ROM)))
        dispatcher = list(struct.unpack_from('>100I', self.rom, 0x174BF0))
        count = 0
        for state, cur, goal, flags, phase, parent in itertools.product((0, 1, 2, 128), range(4), range(4), (0, 8), (0, 8), (False, True)):
            memory = fixture(state, cur, goal, flags=flags)
            put(memory, OWNER + 0x2F, 13, 1)
            put(memory, OWNER + 0x30, 0, 1)
            put(memory, TABLE + 13 * 4, screen.ENTRY)
            ref = RingReference(memory, actual=True).run()
            models = []
            for body in (self.words, self.retail):
                connected = dict(zip(range(velocity.screen.ENTRY, velocity.screen.ENTRY + 76, 4), helper))
                connected.update(zip(range(screen.ENTRY, screen.ENTRY + 268, 4), body))
                model = RingOracle(dispatcher if parent else body, memory, phase=phase,
                    entry=DISPATCHER if parent else screen.ENTRY, connected=connected).run()
                self.assertEqual((model.calls, public_memory(model)), (ref.calls, public_memory(ref)))
                if parent:
                    self.assertEqual(model.callbacks, [OWNER])
                    self.assertEqual(model.releases, [] if ref.result else [OWNER])
                else:
                    self.assertEqual((model.r[2], public_events(model)), (ref.result, ref.events))
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                             (models[1].r, models[1].f, models[1].memory, models[1].events))
            count += 1
        self.receipt('connected', dict(cases=count, integrator_words=19, dispatcher_words=100,
            full_epilogues_and_consumed_false_result_release=True, dispatcher_callback13_second_kind_zero_timer_flag_off_only=True,
            original_dispatcher_separate_from_its_linked_placeholder=True, release_bounded_hook=True,
            hardware_FCSR_and_full_gameplay_not_qualified=True))

    def test_08_installed_slot_callback_table_and_exact_guard_closure(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION], functions[screen.FUNCTION]), (screen.ENTRY, self.retail))
        self.assertEqual(functions['func_151D8718'], list(struct.unpack_from('>19I', self.rom, velocity.screen.ROM)))
        source = (self.root / SOURCE).read_text()
        self.assertIn(source, source_shapes(self.root))
        installed = screen.SELECTED in source
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertEqual(guards[11155:11168], screen.owner_guards() if installed else [])
        found = [struct.unpack_from('>I', data, TABLE + 52 - address)[0] for address, data in
            sections(self.root / 'conker/build/conker.us.elf').values() if address <= TABLE + 52 < address + len(data)]
        self.assertEqual(found, [screen.ENTRY])
        self.receipt('installed', dict(linked_target_integrator_and_callback13_exact=True,
            guard_rows=len(guards), guards_added=13 if installed else 0, complete_guard_history_checked=True))


NATIVE_PREFIX = r'''
typedef signed char s8;typedef unsigned char u8;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;
static u8 arena[8192] __attribute__((aligned(16))),expected[8192] __attribute__((aligned(16)));
f32 D_800BE9A4;static u32 expectedDelta;
static unsigned mutation,used,error;static u32 arguments[512][3];static unsigned expectedCalls;
static u32 tobits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 frombits(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static int signbyte(unsigned v){return v<128?(int)v:(int)v-256;}
static void effect(u8 *bytes,unsigned index,u32 *clock){
 if(index)return;
 if(mutation==1)bytes[0x2D]=0;
 if(mutation==2)bytes[0x2C]=0;
 if(mutation==3)*(u8 **)(bytes+0x94)=arena+0x1C00;
 if(mutation==4)*clock=0xBF800000;
 if(mutation==5){bytes[0x25]=3;bytes[0x2D]=2;}
 if(mutation==6){bytes[0x2D]=0;bytes[0x2C]=255;*(u8 **)(bytes+0x94)=arena+0x1C00;}
}
'''

NATIVE_CHECK = r'''
void func_151D8718(f32 *position,f32 *speed,f32 delta){
 u32 p=(u32)position,v=(u32)speed,d=tobits(delta),clock=tobits(D_800BE9A4);
 if(used>=expectedCalls||p!=arguments[used][0]||v!=arguments[used][1]||d!=arguments[used][2]){error=1;return;}
 *(u32 *)(position+1)^=d;*(u32 *)speed^=0x01010101;
 effect(arena+32,used++,&clock);D_800BE9A4=frombits(clock);
}
static int check(unsigned state,unsigned cur,unsigned goal,unsigned count,unsigned flags,unsigned mode,unsigned size){
 unsigned i,base=256,position,expectedResult;int cursor,stop,phase;u8 *owner=arena+32;
 s32 (*volatile invoke)(u8 *)=func_151D792C;
 for(i=0;i<size;i++)arena[i]=(u8)(i*17+0xA5);
 arena[32+0x2C]=(u8)state;arena[32+0x2D]=(u8)goal;arena[32+0x2E]=(u8)cur;arena[32+0x25]=(u8)count;
 *(u16 *)(owner+0x1E)=(u16)flags;*(u8 **)(owner+0x94)=arena+base;
 D_800BE9A4=frombits(0x3F800000);expectedDelta=0x3F800000;mutation=mode;used=0;error=0;expectedCalls=0;
 for(i=0;i<size;i++)expected[i]=arena[i];
 phase=signbyte(state);cursor=signbyte(cur);stop=signbyte(goal);expectedResult=1;
 if(phase<2&&(flags&8))expectedResult=0;
 else{
  while(cursor!=stop){
   cursor=cursor>0?cursor-1:(int)expected[32+0x25]-1;
   position=base+(unsigned)(cursor*28);
   if(position+16>size||expectedCalls>=512)return 1;
   arguments[expectedCalls][0]=(u32)(arena+position);arguments[expectedCalls][1]=(u32)(arena+position+12);arguments[expectedCalls][2]=expectedDelta;
   *(u32 *)(expected+position+4)^=expectedDelta;*(u32 *)(expected+position+12)^=0x01010101;
   effect(expected+32,expectedCalls++,&expectedDelta);
   stop=signbyte(expected[32+0x2D]);phase=signbyte(expected[32+0x2C]);
  }
  position=base+(unsigned)(stop*28);
  for(i=0;i<3;i++)*(u32 *)(expected+32+0x54+4*i)=phase>0?*(u32 *)(expected+position+4*i):0;
 }
 if((unsigned)invoke(owner)!=expectedResult||used!=expectedCalls||error||tobits(D_800BE9A4)!=expectedDelta)return 2;
 for(i=0;i<size;i++)if(arena[i]!=expected[i])return 3;
 return 0;
}
'''
