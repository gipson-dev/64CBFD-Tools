"""Float32, copy/alias, native and strict image qualification of the leaf step."""

from pathlib import Path
import json
import random
import struct
import subprocess
import unittest

from tools.experiments import game_kinematic_step as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_owner_actor_update_match import read


ROOT = Path(__file__).resolve().parents[2]
BASE, POSITION = 0x28000, 36


def rounded(value):
    return floating(bits(value))


def public(memory, base=BASE):
    return {a: v for a, v in memory.items() if base <= a < base + 96}


def corpus():
    numbers = (4.25, -13.5, 8.75, 16777216.0, -0.0, 1.0000001192092896)
    for delta in (-24, -12, -8, -4, 0, 4, 8, 12, 24):
        for acceleration in (0.0, -9.8, 3.1415927):
            for timestep in (0.0, 0.125, -0.5, 1.0, 8.0):
                yield tuple(bits(numbers[i % len(numbers)]) for i in range(24)), delta, bits(acceleration), bits(timestep)
    rng = random.Random(0x1519BE1C)
    for i in range(128):
        values = tuple(rng.getrandbits(1) << 31 | rng.randrange(90, 146) << 23 | rng.getrandbits(23) for _ in range(24))
        scalar = lambda: rng.getrandbits(1) << 31 | rng.randrange(90, 141) << 23 | rng.getrandbits(23)
        yield values, (-24, -12, -8, -4, 0, 4, 8, 12, 24)[i % 9], scalar(), scalar()


def fixture(case, base=BASE):
    words, _, _, _ = case
    memory = {STACK + i: (i * 13 + 0xA5) & 255 for i in range(-0x200, 0x100)}
    for i, value in enumerate(words):
        put(memory, base + i * 4, value)
    return memory


def reference(initial, case, base=BASE):
    _, delta, acceleration, timestep = case
    p, v = base + POSITION, base + POSITION + delta
    memory, events = initial.copy(), []

    def get(address):
        value = read(memory, address)
        events.append(('R', address, 4, value))
        return value

    def store(address, number):
        value = bits(number)
        put(memory, address, value)
        events.append(('W', address, 4, value))

    saved = [floating(get(v + i * 4)) for i in range(3)]
    acc, dt = floating(acceleration), floating(timestep)
    store(v + 4, rounded(floating(get(v + 4)) + rounded(acc * dt)))
    store(p, rounded(floating(get(p)) + rounded(saved[0] * dt)))
    old_y, old_z = floating(get(p + 4)), floating(get(p + 8))
    vertical = rounded(rounded(saved[1] * dt) +
        rounded(rounded(rounded(0.5 * acc) * dt) * dt))
    store(p + 4, rounded(old_y + vertical))
    store(p + 8, rounded(old_z + rounded(saved[2] * dt)))
    return memory, events


def model(words, initial, case, phase=0, base=BASE, entry=source.ENTRY):
    _, delta, acc, dt = case
    return TriangleOracle(words, initial, phase=phase, entry=entry,
        arguments=(base + POSITION, base + POSITION + delta, acc, dt)).run()


def complete(model):
    return model.r, model.f, model.condition, model.lo, model.memory, model.events, model.calls, model.visits


def native_harness(body, cases):
    rows = []
    for case in cases:
        words, delta, acc, dt = case
        assert delta % 12 == 0
        expected, _ = reference(fixture(case), case)
        output = [read(expected, BASE + i * 4) for i in range(24)]
        row = lambda seq: '{' + ','.join('0x%08Xu' % x for x in seq) + '}'
        rows.append('{%s,%s,%d,0x%08Xu,0x%08Xu}' % (row(words), row(output), delta // 12, acc, dt))
    return '''typedef unsigned int u32;
typedef float f32;
''' + source.DECLARATIONS + '''
typedef char vector_size_is_12[sizeof(KinematicVector) == 12 ? 1 : -1];
''' + body + '''
static f32 scalar(u32 word) { union {u32 u; f32 f;} v; v.u=word; return v.f; }
static u32 word(f32 value) { union {u32 u; f32 f;} v; v.f=value; return v.u; }
typedef struct { u32 input[24], expected[24]; int delta; u32 acc, dt; } Case;
static const Case cases[] = {
''' + ',\n'.join(rows) + '''
};
static int test_all(void) {
    unsigned int c, i;
    KinematicVector bank[8];
    for (c=0; c<sizeof(cases)/sizeof(cases[0]); c++) {
        const Case *item=&cases[c];
        for (i=0; i<8; i++) {
            bank[i].x=scalar(item->input[i*3]);
            bank[i].y=scalar(item->input[i*3+1]);
            bank[i].z=scalar(item->input[i*3+2]);
        }
        func_1519BE1C(&bank[3], &bank[3+item->delta], scalar(item->acc), scalar(item->dt));
        for (i=0; i<8; i++) {
            if (word(bank[i].x)!=item->expected[i*3] ||
                word(bank[i].y)!=item->expected[i*3+1] ||
                word(bank[i].z)!=item->expected[i*3+2]) return 23;
        }
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=test_all();
    __asm__ volatile("int $0x80" : : "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class KinematicStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD
        cls.installed = source.digest((ROOT / source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            source.qualify(ROOT, cls.output)
            source.make_shadow(ROOT, cls.output)
            source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output)
        cls.obj, diagnostics = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n' + source.DECLARATIONS + source.SELECTED, 'fresh-selected')
        if diagnostics:
            raise ValueError(diagnostics)
        raw, cls.bindings = source.payload(cls.obj)
        cls.words = list(struct.unpack('>39I', raw))
        cls.original = source.original(ROOT, cls.output)
        cls.truth = list(struct.unpack_from('>39I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.cases = list(corpus())
        cls.native_cases = [case for case in cls.cases if case[1] % 12 == 0]
        cls.receipt = dict(cases=len(cls.cases), native_cases=len(cls.native_cases),
            installed=cls.installed, matching_credit=int(cls.installed), guards=0, compiler_only=True)

    @classmethod
    def tearDownClass(cls):
        (cls.output / 'test-receipt.json').write_text(json.dumps(cls.receipt, indent=2) + '\n')
        print('kinematic qualification:', cls.receipt)

    def native(self, body, label, optimization='-O2'):
        unit = self.output / (label + '.c')
        unit.write_text(native_harness(body, self.native_cases))
        binary = self.output / (label + optimization)
        command = ['gcc', '-m32', optimization, '-std=c99', '-fno-strict-aliasing',
            '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffreestanding', '-nostdlib',
            '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-ffp-contract=off',
            '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error',
            '-Wall', '-Wextra', '-Werror', str(unit), '-o', str(binary)]
        compiled = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        return subprocess.run([str(binary)], capture_output=True, timeout=30)

    def test_complete_direct_C_original_slot_zero_bindings_and_o32_shape(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual(source.payload(self.original), source.payload(self.obj))
        self.assertEqual(self.bindings, {})
        self.assertEqual(self.words[:3], [0x44866000, 0x44877000, 0x27BDFFF0])
        self.assertEqual(self.words[-2:], [0x03E00008, 0x27BD0010])
        self.assertIn('KinematicVector saved = *velocity;', source.SELECTED)
        self.assertIn('/* Advance position', source.SELECTED)
        asm = self.values[source.ASM].decode()
        self.assertEqual(asm.count('jal        ' + source.FUNCTION), 2)
        self.assertIn('15199AF0 0D466F87', asm)
        self.assertIn('15199FC0 0D466F87', asm)
        with self.assertRaises(ValueError):
            source.recovered_owner(self.values[source.SOURCE].decode().replace('s32 func_1519BE1C()', 'void wrong_name()'))

    def test_reference_public_access_order_complete_states_and_all_word_coverage(self):
        visits, phases, aliases = set(), 0, 0
        for case in self.cases:
            initial = fixture(case)
            expected, events = reference(initial, case)
            for phase in (0, 8):
                a = model(self.truth, initial, case, phase)
                b = model(self.words, initial, case, phase)
                self.assertEqual(complete(a), complete(b))
                self.assertEqual(public(b.memory), public(expected), case)
                observed = [event for event in b.events if BASE <= event[1] < BASE + 96]
                self.assertEqual(observed, events, case)
                visits.update(b.visits)
                phases += 1
                aliases += int(abs(case[1]) < 12)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)))
        before = self.values['conker/build/conker.us.elf']
        at = source.elf_slot_offset(before, source.ENTRY, source.SIZE)
        placeholder = list(struct.unpack_from('>39I', before, at))
        control_case = self.cases[1]
        initial = fixture(control_case)
        control = model(placeholder, initial, control_case)
        expected, _ = reference(initial, control_case)
        self.assertNotEqual(public(control.memory), public(expected))
        self.receipt.update(model_phases=phases, complete_final_states=phases,
            retail_words_visited=len(visits), physical_overlap_phases=aliases,
            hardware_FCSR_modeled=False, predecessor_placeholder_negative=True)

    def test_native32_typed_vector_aliases_float32_three_optimizations_and_UBSan(self):
        for optimization in ('-O0', '-O2', '-O3'):
            result = self.native(source.SELECTED, 'native', optimization)
            self.assertEqual(result.returncode, 0, (optimization, result.stdout, result.stderr))
        self.receipt.update(native_optimizations=3, trap_UBSan=True)

    def test_compiled_saved_velocity_acceleration_half_step_and_rounding_negatives(self):
        mutations = {
            'live-velocity': source.SELECTED.replace('KinematicVector saved = *velocity;', 'KinematicVector *saved = velocity;').replace('saved.', 'saved->'),
            'no-velocity-update': source.SELECTED.replace('    velocity->y += acceleration * timestep;\n', ''),
            'full-acceleration': source.SELECTED.replace('0.5f * acceleration', '1.0f * acceleration'),
            'negative-acceleration': source.SELECTED.replace('velocity->y +=', 'velocity->y -='),
            'reassociated': source.SELECTED.replace('0.5f * acceleration * timestep * timestep', 'acceleration * (0.5f * timestep * timestep)'),
        }
        for name, body in mutations.items():
            self.assertNotEqual(body, source.SELECTED)
            result = self.native(body, 'negative-' + name)
            self.assertEqual(result.returncode, 23, (name, result.stdout, result.stderr))
        self.receipt['effective_compiled_semantic_negatives'] = len(mutations)

    def test_independent_GNU_code_and_argument_data_rebases(self):
        count = 0
        for i, (code_delta, data_delta) in enumerate(((0x10000, 0x3000), (0x100000, -0x10000), (0x2000000, 0x8000))):
            words = []
            for label, obj in (('C', self.obj), ('original', self.original)):
                script = self.output / ('rebase-%d-%s.ld' % (i, label))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + code_delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-T', str(script), '-e', source.FUNCTION,
                    '-o', str(elf), str(obj)], check=True, capture_output=True)
                address, text = sections(elf)['.text']
                self.assertEqual(address, source.ENTRY + code_delta)
                words.append(list(struct.unpack('>39I', text[:156])))
            self.assertEqual(words[0], words[1])
            for case in self.cases[::67]:
                base = BASE + data_delta
                initial = fixture(case, base)
                expected, _ = reference(initial, case, base)
                for phase in (0, 8):
                    a = model(words[0], initial, case, phase, base, source.ENTRY + code_delta)
                    b = model(words[1], initial, case, phase, base, source.ENTRY + code_delta)
                    self.assertEqual(complete(a), complete(b))
                    self.assertEqual(public(a.memory, base), public(expected, base))
                    count += 1
        self.receipt.update(independent_GNU_rebases=3, rebased_model_phases=count,
            bindings_to_rebase=0)

    def test_actual_owner_Make_padding_and_strict_full_image_scope_negatives(self):
        report = json.loads((self.output / 'qualification.json').read_text())
        self.assertTrue(report['compiler_only'])
        self.assertGreater(report['preserved_neighbors'], 0)
        self.assertEqual(source.same_functions(self.output / 'before-owner.o', self.output / 'after-owner.o',
            (source.FUNCTION,)), report['preserved_neighbors'])
        self.assertEqual(json.loads((self.output / 'make-shadow.json').read_text())['actual_Make_commands'], 3)
        before = self.values['conker/build/conker.us.elf']
        truth = self.values['conker/conker.us.bin'][source.ROM:source.ROM + source.SIZE]
        actual = (self.output / 'first-linked.elf').read_bytes()
        source.check_image(before, actual, truth)
        at = source.elf_slot_offset(before, source.ENTRY, source.SIZE)
        size = next(offset + 8 for offset, name, _, _ in source.symbol_rows(before) if name == source.FUNCTION)
        for offset in (0, at - 1, at, at + 155, at + 156, size + 3):
            wrong = bytearray(actual)
            wrong[offset] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(wrong), truth)
        for wrong in (actual[:-1], actual + b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before, wrong, truth)
        self.receipt.update(preserved_neighbors=report['preserved_neighbors'], wrong_image_controls=8)

    def test_live_installed_or_unchanged_predecessor_and_no_new_guards(self):
        if self.installed:
            self.assertTrue(source.audit(ROOT, self.output)['strict_first_link_reproduced'])
        else:
            for name, old in self.values.items():
                self.assertEqual((ROOT / name).read_bytes(), old, name)
        self.assertEqual((ROOT / 'conker/retail_word_patches.us.csv').read_bytes(),
            self.values['conker/retail_word_patches.us.csv'])


if __name__ == '__main__':
    unittest.main()
