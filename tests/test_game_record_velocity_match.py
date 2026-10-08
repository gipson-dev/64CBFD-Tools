"""Complete vertical integration, alias ordering and mixed pointer/float ABI."""

import csv
import itertools
import json
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_velocity_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

SOURCE = 'conker/src/game/generated_204660.c'
BUFFER = 0x20000
FINITE = (0, 0x80000000, 1, 0x80000001, 0x007FFFFF, 0x00800000,
          0x3F000000, 0x3F800000, 0xBF800000, 0x41200000, 0xC2480000,
          0x7F7FFFFF, 0xFF7FFFFF)
SPECIAL = (0x7F800000, 0xFF800000, 0x7FC00001, 0xFFC12345, 0x7F800001)


def fixture(values=(0x41200000, 0xBF800000, 0x3E6F9DB3, 0x3DEF9DB3), layout=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {BUFFER + i: 0xA5 for i in range(-16, 64)}
    position, velocity = BUFFER + 8, BUFFER + 24
    for address, value in zip((position + 4, velocity, *symbols.values()), values):
        put(memory, address, value)
    if layout == 1:
        velocity = position + 4
    elif layout == 2:
        velocity = position
        put(memory, velocity, values[1])
    elif layout in (3, 4):
        velocity = list(symbols.values())[layout - 3]
    elif layout in (5, 6):
        position = list(symbols.values())[layout - 5] - 4
    return memory, position, velocity


def reference(memory, position, velocity, delta, symbols=None):
    symbols = symbols or screen.SYMBOLS
    result, events = dict(memory), []

    def load(address):
        assert address % 4 == 0 and all(address + i in result for i in range(4)), ('unmapped load', address)
        word = read(result, address)
        events.append(('R', address, 4, word))
        return word

    def store(address, word):
        events.append(('W', address, 4, word))
        assert address % 4 == 0 and all(address + i in result for i in range(4)), ('unmapped store', address)
        put(result, address, word)

    d = floating(delta)
    acceleration = floating(load(symbols['D_800AB2EC']))
    old = floating(load(velocity))
    step = floating(bits(acceleration * d))
    updated = bits(old + step)
    square = floating(bits(d * d))
    store(velocity, updated)
    half = floating(load(symbols['D_800AB2F0']))
    height = floating(load(position + 4))
    second = floating(bits(half * square))
    first = floating(bits(old * d))
    displacement = floating(bits(first + second))
    store(position + 4, bits(height + displacement))
    return result, events


def cases():
    for h, v, d in itertools.product(FINITE, repeat=3):
        yield (h, v, 0x3E6F9DB3, 0x3DEF9DB3), d
    rng = random.Random(0x151D8718)
    for _ in range(256):
        values = tuple(rng.getrandbits(32) for _ in range(5))
        yield values[:4], values[4]
    for special, field in itertools.product(SPECIAL, range(5)):
        values = [0x41200000, 0xBF800000, 0x3E6F9DB3, 0x3DEF9DB3, 0x3F800000]
        values[field] = special
        yield tuple(values[:4]), values[4]


class CallerOracle(TriangleOracle):
    def execute(self, word):
        if word >> 26 == 32:
            CopyOracle.execute(self, word)
        else:
            super().execute(word)

    def record_call(self, target):
        assert target == screen.ENTRY
        self.calls.append(tuple(self.r[4:7]))


class GameRecordVelocityTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-velocity-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>19I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def model(self, words, memory, position, velocity, delta, phase=0, entry=screen.ENTRY):
        return TriangleOracle(words, memory, phase=phase, entry=entry,
                              arguments=(position, velocity, delta)).run()

    def compare(self, values, delta, layout=0, phase=0, words=None, symbols=None, entry=screen.ENTRY):
        memory, position, velocity = fixture(values, layout, symbols)
        expected, events = reference(memory, position, velocity, delta, symbols)
        model = self.model(words if words is not None else self.words, memory, position, velocity, delta, phase, entry)
        self.assertEqual((model.memory, model.events), (expected, events))
        if symbols is None and entry == screen.ENTRY:
            retail = self.model(self.retail, memory, position, velocity, delta, phase)
            self.assertEqual((model.r, model.f, model.events, model.memory),
                             (retail.r, retail.f, retail.events, retail.memory))
        return model

    def test_01_complete_slot_mixed_abi_and_stale_guards(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (19, 0, 3))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(sum(map(len, self.record['relocations'].values())), 4)
        for index in (0, 3, 6, 13):
            stale = self.raw.copy()
            stale[index] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        profiles = []
        for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
            meta, _ = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            profiles.append(meta)
        self.assertEqual([(m['body_words'], m['frame'], m['differences']) for m in profiles],
                         [(19, 0, 3), (18, 0, 7), (25, 8, 25), (25, 8, 25)])
        self.receipt('slot', dict(words=19, bytes=76, frame=0, direct_words=16, guards=3,
            relocations=4, stale_rejections=4, profiles=profiles, float_argument_in_A2_then_F12=True))

    def test_02_finite_special_aliases_and_full_normalized_state(self):
        count, seen, raw_count = 0, set(), 0
        for values, delta in cases():
            for layout, phase in itertools.product(range(7), (0, 8)):
                model = self.compare(values, delta, layout, phase)
                seen.update(model.visits)
                count += 1
            if all(v & 0x7F800000 != 0x7F800000 for v in (*values, delta)):
                memory, position, velocity = fixture(values)
                raw = self.model(self.raw, memory, position, velocity, delta)
                expected, events = reference(memory, position, velocity, delta)
                self.assertEqual((raw.events, raw.memory), (events, expected))
                raw_count += 1
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 76, 4)))
        self.receipt('guest', dict(cases=count, layouts=7, SP_phases=2, raw_finite_cases=raw_count,
            all_19_words_reached=True, complete_normalized_GP_FP_memory_trace_equality=True,
            NaN_payload_FCSR_hardware_not_modeled=True))

    def test_03_fault_prefixes(self):
        count = 0
        for layout in range(7):
            memory, position, velocity = fixture(layout=layout)
            for address in dict.fromkeys((*screen.SYMBOLS.values(), velocity, position + 4)):
                broken = dict(memory)
                del broken[address + 3]
                models = [TriangleOracle(w, broken, arguments=(position, velocity, 0x3F800000))
                          for w in (self.words, self.retail)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                self.assertEqual((models[0].events, models[0].memory, models[0].r, models[0].f),
                                 (models[1].events, models[1].memory, models[1].r, models[1].f))
                count += 1
        self.receipt('faults', dict(cases=count, complete_prefix_equality=True,
            guest_fault_order_not_portable_C_or_CP0_metadata=True))

    def test_04_actual_native32_C_and_canaries(self):
        vectors = []
        for values, delta in cases():
            if any(v & 0x7F800000 == 0x7F800000 for v in (*values, delta)):
                continue
            for mode in range(5):
                memory, position, velocity = fixture(values, mode)
                expected, _ = reference(memory, position, velocity, delta)
                before = [read(memory, BUFFER + i * 4) for i in range(8)] + list(values[2:])
                after = [read(expected, BUFFER + i * 4) for i in range(8)] + [read(expected, a) for a in screen.SYMBOLS.values()]
                vectors.append('{ {%s}, 0x%Xu, %d, {%s} }' %
                    (','.join('0x%Xu' % v for v in before), delta, mode, ','.join('0x%Xu' % v for v in after)))
        self.fixture = NATIVE_PREFIX + screen.SELECTED + '\n' + NATIVE_CHECK + '\n' + (
            'static const struct Vector vectors[] = {\n' + ',\n'.join(vectors) + '\n};\n')
        self.run_host('unsigned i; if(sizeof(void *)!=4 || sizeof(float)!=4)return 10;\n'
            'for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)if(check(&vectors[i]))return 11;')
        self.receipt('native', dict(executions=len(vectors), layouts=5, unchanged_buffer_words_and_globals_checked=True,
            actual_C_through_volatile_function_pointer=True, independent_step_rounded_golden_vectors=True,
            NaN_classification_not_payload_asserted=True, target_FCSR_not_emulated=True))

    def test_05_source_controls(self):
        inputs = list(cases())
        inputs = inputs[::37] + inputs[-281:]
        inputs = [(v, d) for v, d in inputs if all(w & 0x7F800000 != 0x7F800000 for w in (*v, d))]
        records, ordinary, negatives = [], 0, 0
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            if name == 'old-style':
                # A K&R float parameter is promoted; it is a compiler/ABI probe, not this prototype.
                continue
            outcomes = []
            for values, delta in inputs:
                for layout in (0, 1, 4):
                    memory, position, velocity = fixture(values, layout)
                    expected, _ = reference(memory, position, velocity, delta)
                    model = self.model(words, memory, position, velocity, delta)
                    outcomes.append(model.memory == expected)
            if name.startswith('negative-'):
                self.assertFalse(all(outcomes), name)
                negatives += 1
            else:
                self.assertTrue(all(outcomes), name)
                ordinary += len(outcomes)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary,
            effective_negatives=negatives, K_and_R_probe_measurement_only=True, measurements=records))

    def test_06_copied_owner_padder_relocations_and_links(self):
        source = (self.root / SOURCE).read_text().replace(screen.SELECTED, screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL), 1)
        objects, diagnostics = [], []
        for name, body in (('baseline', source), ('selected', source.replace(screen.ORIGINAL, screen.SELECTED))):
            obj, warnings = compile_owner(self.root, self.out, body, 'owner-' + name)
            diagnostics.append(warnings)
            processed = self.out / ('owner-' + name + '-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(processed)
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
        target = current[screen.FUNCTION]
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(text[target['value']:target['value'] + 76], isolated[:76])
        self.assertEqual({o - target['value']: r for o, r in rel.items() if target['value'] <= o < target['value'] + 76}, isolated_rel)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            reader = csv.DictReader(stream)
            fields, guards = reader.fieldnames, list(reader)
        assert_guard_history(self, guards[:11152])
        if len(guards) == 11152:
            guards += screen.owner_guards()
        else:
            self.assertEqual(guards[11152:11155], screen.owner_guards())
        manifest = self.out / 'qualification-guards.csv'
        with manifest.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(guards)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s', word_patches_path=manifest, filename='generated_204660')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'], 76)
        self.assertEqual(relocations, isolated_rel)
        executions = 0
        for index, base in enumerate((0x800AB2EC, 0x80007FFC, 0xFFFF7FFC, 0x7FFF8000, 0x81018004, 0x00107FF8)):
            entry = screen.ENTRY + (0x1000004 if index == 1 else 0)
            symbols = {name: (base + n * 4) & 0xFFFFFFFF for n, name in enumerate(screen.SYMBOLS)}
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>19I', sections(elf)['.text'][1]))
            expected = self.retail.copy()
            for offset, rows in relocations.items():
                self.assertEqual(len(rows), 1)
                kind, name = rows[0]
                value = symbols[name]
                self.assertIn(kind, ('R_MIPS_HI16', 'R_MIPS_LO16'))
                if kind == 'R_MIPS_HI16':
                    value = (value + 0x8000) >> 16
                expected[offset // 4] = expected[offset // 4] & 0xFFFF0000 | value & 65535
            self.assertEqual(words, expected)
            for layout, delta, phase in itertools.product(range(7), FINITE[:10], (0, 8)):
                self.compare((0x41200000, 0xBF800000, 0x3E6F9DB3, 0x3DEF9DB3), delta, layout, phase, words, symbols, entry)
                executions += 1
        self.receipt('owner-padder', dict(neighbors=len(current) - 1, unchanged_warning_count=len(diagnostics[0]),
            pools_relative_relocations_unchanged=True, isolated_owner_words_equal=True, padded_bytes=76,
            independent_links=6, rebased_executions=executions, relocations=4, guards=3))

    def test_07_installed_link_constants_and_guard_history(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION], functions[screen.FUNCTION]), (screen.ENTRY, self.retail))
        address, data = sections(self.root / 'conker/build/conker.us.elf')['.game_data']
        for name, word in zip(screen.SYMBOLS, (0x3E6F9DB3, 0x3DEF9DB3)):
            self.assertEqual(struct.unpack_from('>I', data, screen.SYMBOLS[name] - address)[0], word)
        source = (self.root / SOURCE).read_text()
        installed = screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL), 1)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertEqual(guards[11152:11155], screen.owner_guards() if installed else [])
        proposed = guards[:11152] + screen.owner_guards()
        assert_guard_history(self, proposed)
        for i in range(3):
            bad = [dict(row) for row in proposed]
            bad[11152 + i]['replacement'] = '0x00000000'
            with self.assertRaises(AssertionError):
                assert_guard_history(self, bad)
        for bad in (proposed[:-1], proposed + [dict(proposed[-1])], proposed[:11152] + list(reversed(screen.owner_guards()))):
            with self.assertRaises(AssertionError):
                assert_guard_history(self, bad)
        self.receipt('installed', dict(complete_linked_target_and_actual_constants_exact=True,
            guards=3, prior_rows=11152, full_callers_hardware_gameplay_not_qualified=True))

    def test_08_complete_actual_ring_caller_connection(self):
        caller, owner, records, clock = 0x151D792C, 0x24000, 0x26000, 0x800BE9A4
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        caller_words = list(struct.unpack_from('>67I', rom, 0x204DDC))
        count, seen = 0, set()
        for state, current, stop, enabled, delta, phase in itertools.product(
                (0, 1, 2), range(4), range(4), (0, 8), (0, 0x3F800000, 0xBF800000, 0x41200000), (0, 8)):
            memory, _, _ = fixture()
            memory.update({STACK + i: 0xA5 for i in range(-0x100, 0x100)})
            memory.update({owner + i: 0xA5 for i in range(0xA0)})
            memory.update({records + i: 0xA5 for i in range(4 * 0x1C)})
            for address, value, size in ((owner + 0x2C, state, 1), (owner + 0x2D, stop, 1),
                    (owner + 0x2E, current, 1), (owner + 0x25, 4, 1), (owner + 0x1E, enabled, 2),
                    (owner + 0x94, records, 4), (clock, delta, 4)):
                put(memory, address, value, size)
            for index in range(4):
                for field, value in enumerate((index + 1., index + 2., index + 3., -index - 1.)):
                    put(memory, records + index * 0x1C + field * 4, bits(value))
            expected, calls = dict(memory), []
            gated = state < 2 and bool(enabled & 8)
            if not gated:
                index = current
                while index != stop:
                    index = (index - 1) % 4
                    pointer = records + index * 0x1C
                    expected, _ = reference(expected, pointer, pointer + 0xC, delta)
                    calls.append((pointer, pointer + 0xC, delta))
                for field in range(3):
                    put(expected, owner + 0x54 + field * 4,
                        read(expected, records + stop * 0x1C + field * 4) if state > 0 else 0)
            models = []
            for words in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 76, 4), words))
                model = CallerOracle(caller_words, memory, phase=phase, entry=caller,
                                     arguments=(owner,), connected=connected).run()
                public = lambda m: {a: v for a, v in m.items() if not STACK - 0x100 <= a < STACK + 0x100}
                self.assertEqual((model.calls, public(model.memory), model.r[2]), (calls, public(expected), int(not gated)))
                self.assertEqual(model.r[29], STACK + phase)
                seen.update(model.visits)
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                             (models[1].r, models[1].f, models[1].memory, models[1].events))
            count += 1
        self.assertTrue(set(range(screen.ENTRY, screen.ENTRY + 76, 4)) <= seen)
        self.receipt('connected', dict(cases=count, actual_caller_words=67, complete_caller_including_epilogue=True,
            ring_wrap_empty_enabled_gate_and_coordinate_copy=True, helper_mixed_ABI_and_all_19_words_reached=True,
            second_caller_FCSR_hardware_gameplay_not_qualified=True))


NATIVE_PREFIX = r'''
typedef unsigned int u32;typedef float f32;
f32 D_800AB2EC,D_800AB2F0;
static f32 storage[8];
static f32 frombits(u32 v){union {u32 u;f32 f;} p;p.u=v;return p.f;}
static u32 tobits(f32 v){union {u32 u;f32 f;} p;p.f=v;return p.u;}
'''

NATIVE_CHECK = r'''
struct Vector {u32 before[10];u32 delta;unsigned mode;u32 after[10];};
static int equal(u32 a,u32 b){
 if((b&0x7F800000U)==0x7F800000U&&(b&0x7FFFFFU))
   return (a&0x7F800000U)==0x7F800000U&&(a&0x7FFFFFU);
 return a==b;
}
static int check(const struct Vector *v){
 unsigned i;f32 *velocity=storage+6;
 void (*volatile invoke)(f32 *,f32 *,f32)=func_151D8718;
 for(i=0;i<8;i++)storage[i]=frombits(v->before[i]);
 D_800AB2EC=frombits(v->before[8]);D_800AB2F0=frombits(v->before[9]);
 if(v->mode==1)velocity=storage+3;
 if(v->mode==2)velocity=storage+2;
 if(v->mode==3)velocity=&D_800AB2EC;
 if(v->mode==4)velocity=&D_800AB2F0;
 invoke(storage+2,velocity,frombits(v->delta));
 for(i=0;i<8;i++)if(!equal(tobits(storage[i]),v->after[i]))return 1;
 if(!equal(tobits(D_800AB2EC),v->after[8])||!equal(tobits(D_800AB2F0),v->after[9]))return 2;
 return 0;
}
'''
