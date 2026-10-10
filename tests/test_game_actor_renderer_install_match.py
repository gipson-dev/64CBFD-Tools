"""Both complete renderer bodies, aliased colors and whole linked installation."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_color_provider_candidates as color
from tools.experiments import game_actor_renderer_matching as renderer
from tools.experiments import game_actor_renderer_connected as chain
from tools.experiments import game_object_color_mode_matching as fog_c
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_renderer_schedule as schedule
from tools.tests import test_game_actor_renderer_recovery as proof
from tools.tests.test_game_record_constructor_match import elf_slot_offset, elf_symbol_size_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_actor_renderer_native32 as native
from tools.tests.test_game_row_destination_fill import START

COLORS = 0x2E000

NATIVE_FIXTURE = r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;typedef float f32;
u8 D_800D9B68[16] __attribute__((aligned(16))),D_800D9B78[16] __attribute__((aligned(16)));
static u8 actor[0x32C] __attribute__((aligned(16))),parameters[16] __attribute__((aligned(16)));
static u8 outputs[80] __attribute__((aligned(16)));static f32 amount;
static f32 D_80096F38=2.55f,D_80096F3C=0.02454369329f;
static f32 cosf(f32 phase) { (void)phase;return 0.5f; }
static void copy(u8 *to,const u8 *from,u32 size) { u32 i;for(i=0;i<size;i++)to[i]=from[i]; }
typedef char widths[(sizeof(void *)==4 && sizeof(s32)==4)?1:-1];
typedef struct {
    u8 actor[0x32C],expectedActor[0x32C],prim[16],expectedPrim[16],env[16],expectedEnv[16];
    u8 parameters[16],expectedParameters[16],outputs[80],expectedOutputs[80];
    u32 alpha,view,amount,pointed;s32 *pointers[10];
} Case;
static int report(u32 code,u32 c,u32 i) {
    u32 data[3]={code,c,i};s32 result;
    __asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");
    return (s32)code;
}
'''

NATIVE_RUNNER = r'''
int run(void) {
    u32 c,i;u8 expected[0x32C];const Case *test;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        test=cases+c;
        copy(actor,test->actor,0x32C);copy(expected,test->expectedActor,0x32C);
        copy(D_800D9B68,test->prim,16);copy(D_800D9B78,test->env,16);
        copy(parameters,test->parameters,16);copy(outputs,test->outputs,80);
        *(u32 *)&amount=test->amount;
        if(test->pointed) { *(u32 *)(actor+0xA0)=(u32)&amount;*(u32 *)(expected+0xA0)=(u32)&amount; }
        func_1502CC34(actor,(s32)test->view,(s32)test->alpha,(s32 *)parameters,
            test->pointers[0],test->pointers[1],test->pointers[2],
            test->pointers[3],test->pointers[4],test->pointers[5],
            test->pointers[6],test->pointers[7],test->pointers[8],test->pointers[9]);
        for(i=0;i<0x32C;i++)if(actor[i]!=expected[i])return report(1,c,i);
        for(i=0;i<16;i++)if(D_800D9B68[i]!=test->expectedPrim[i])return report(2,c,i);
        for(i=0;i<16;i++)if(D_800D9B78[i]!=test->expectedEnv[i])return report(3,c,i);
        for(i=0;i<16;i++)if(parameters[i]!=test->expectedParameters[i])return report(4,c,i);
        for(i=0;i<80;i++)if(outputs[i]!=test->expectedOutputs[i])return report(5,c,i);
    }
    return 0;
}
'''


def reference(memory, arguments, cosine=0.5):
    state = memory.copy()
    actor, view, alpha, parameters, *outputs = arguments
    view = chain.signed(view)
    for output, base, channel in zip(outputs[:6], [chain.PRIMITIVE] * 3 + [chain.ENVIRONMENT] * 3, (0, 1, 2, 0, 1, 2)):
        value = proof.guest.read(state, (base + view * 3 + channel) & 0xFFFFFFFF, 1)
        proof.guest.put(state, output, value)
    for output in outputs[6:9]: proof.guest.put(state, output, 0)
    proof.guest.put(state, outputs[9], proof.guest.read(state, parameters + 12, 4))
    if proof.guest.read(state, actor + 0xA4, 1):
        with patch.object(chain.fog, 'public', lambda data: data):
            state, _, _ = chain.fog.reference(state, (actor, *outputs[6:]), cosine)
    return state


class GameActorRendererInstallMatchTests(unittest.TestCase):
    assemble = classmethod(schedule.GameActorRendererScheduleTests.assemble.__func__)
    write_rows = classmethod(schedule.GameActorRendererScheduleTests.write_rows.__func__)
    link = classmethod(schedule.GameActorRendererScheduleTests.link.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-install-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=renderer.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out / 'baseline.json').exists():
            baseline = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                baseline[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        cls.color_meta, cls.color = color.compile_candidate(cls.root, cls.out, 'color')
        cls.render_meta, cls.raw = renderer.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.original_color = list(struct.unpack_from('>50I', cls.rom, color.ROM))
        cls.original_renderer = list(struct.unpack_from('>532I', cls.rom, renderer.ROM))
        cls.bodies, cls.data = chain.load_helpers(cls.root)
        cls.bodies[color.ENTRY] = cls.color
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split('glabel ' + renderer.FUNCTION, 1)[1].split(
            'endlabel ' + renderer.FUNCTION, 1)[0]
        cls.slot = cls.out / 'slot.s'
        cls.slot.write_text('glabel ' + renderer.FUNCTION + assembly + 'endlabel ' + renderer.FUNCTION + '\n')
        cls.rows = renderer.guard_rows(cls.out / 'selected.o')
        cls.write_rows(cls.out / 'isolated.csv', cls.rows)
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80'))
        cls.fitted = cls.link('fitted', proof.S)
        cls.coverage = set()

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def run_native(self, name, source, profile='-O2'):
        path = self.out / (name + '.c')
        binary = self.out / name
        path.write_text(source)
        result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
            '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffreestanding', '-nostdlib', '-static',
            '-fno-pie', '-no-pie', '-fno-stack-protector', '-ffp-contract=off', '-fno-builtin-cosf',
            '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-unused-variable',
            str(path), '-o', str(binary)], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout + result.stderr), (0, ''))
        result = subprocess.run([str(binary)], capture_output=True, timeout=30)
        detail = list(struct.unpack('<3I', result.stderr)) if len(result.stderr) == 12 else result.stderr.hex()
        return result.returncode, detail

    def color_model(self, memory, args, words=None, phase=0, cosine=0.5):
        bodies = dict(self.bodies)
        bodies[color.ENTRY] = self.color if words is None else words
        model = chain.ConnectedOracle(self.fitted, memory, args, bodies, self.data, phase=phase, cosine=cosine)
        model.entry = color.ENTRY
        return model

    def fixture(self, kind=0, view=0, direct=83, amount=10.25):
        memory = {**chain.fixture(view=view, kind=kind, direct=direct, amount=amount), **self.data}
        memory.update({COLORS + i: 0xA5 for i in range(80)})
        for base in (chain.PRIMITIVE, chain.ENVIRONMENT):
            for i in range(-4, 16): memory.setdefault(base + i, 0xA5)
        return memory

    def compare(self, memory, args, phase=0, cosine=0.5):
        models = [self.color_model(memory, args, words, phase, cosine) for words in (self.original_color, self.color)]
        # Include O32's actual unused-alpha home before interpreting private aliases.
        expected = models[0].memory.copy()
        proof.guest.put(expected, proof.STACK + phase + 8, args[2])
        expected = reference(expected, args, cosine)
        for model in models: model.run()
        self.assertEqual((models[0].r[2], models[0].memory, models[0].events, models[0].calls),
            (models[1].r[2], models[1].memory, models[1].events, models[1].calls))
        self.assertEqual({a: value for a, value in models[0].memory.items() if proof.public(a)},
            {a: value for a, value in expected.items() if proof.public(a)})
        self.coverage.update(models[0].visits)
        return models

    def test_01_direct_complete_color_body_and_unused_alpha_home(self):
        self.assertEqual((self.color_meta['body_words'], self.color_meta['frame'],
            self.color_meta['pool_bytes'], self.color_meta['diagnostics']), (50, 0x20, 0, ''))
        self.assertEqual(self.color, self.original_color)
        self.assertEqual(self.color[2], 0xAFA60028)
        self.assertEqual(self.fitted, self.original_renderer)
        self.receipt('shape', color_words=50, color_bytes=200, frame=0x20, color_guards=0,
            unused_alpha_home_exact=True, renderer_words=532, renderer_frame=0x150,
            renderer_guards=531, missing_body_padding=0)

    def test_02_all_color_modes_views_alphas_and_live_output_aliases(self):
        cases = 0
        outputs = tuple(COLORS + i * 4 for i in range(10))
        for kind, phase in itertools.product(range(256), (0, 8)):
            view = (-1, 0, 3, 0x12340002)[kind % 4]
            args = (proof.S['D_800CC2D0'], view, (-1, 0, 255, 0x7FFFFFFF)[kind % 4], proof.PARAMETERS, *outputs)
            self.compare(self.fixture(kind, view), args, phase, cosine=(-1.0, 0.5, 1.0)[kind % 3])
            cases += 1
        for kind, index, target in itertools.product((0, 1, 2, 3, 6, 7, 255), range(10),
                (COLORS, proof.PARAMETERS + 12, proof.S['D_800CC2D0'] + 0xA4, chain.PRIMITIVE)):
            changed = list(outputs)
            changed[index] = target
            args = (proof.S['D_800CC2D0'], 0, 255, proof.PARAMETERS, *changed)
            self.compare(self.fixture(kind), args)
            cases += 1
        for direct, amount in itertools.product((0, 1, 254, 255, chain.FLOAT),
                (-100.0, -0.0, 0.0, 0.25, 10.25, 254.9, 255.0, 300.0)):
            args = (proof.S['D_800CC2D0'], 0, -0x80000000, proof.PARAMETERS, *outputs)
            self.compare(self.fixture(1, direct=direct, amount=amount), args)
            cases += 1
        self.assertTrue(set(range(color.ENTRY, color.ENTRY + 200, 4)).issubset(self.coverage))
        self.receipt('guest', cases=cases, executions=cases * 2, color_words_covered=50,
            all_256_fog_modes=True, signed_fullwidth_views=True, full_memory_order_exact=True,
            independent_ordered_public_reference=True, output_aliases_reload_live_inputs=True,
            actual_full_fog_body=True, cosine_bounded=True)

    def test_03_complete_color_private_aliases_and_fired_fault_prefixes(self):
        aliases = prefixes = 0
        outputs = tuple(COLORS + i * 4 for i in range(10))
        inputs = []
        for phase in (0, 8):
            changed = tuple(proof.STACK + phase + 0x80 + i * 4 for i in range(10))
            args = (proof.S['D_800CC2D0'], 0, 0x87654321, proof.PARAMETERS, *changed)
            self.compare(self.fixture(6), args, phase)
            aliases += 1
            inputs.append((self.fixture(1, direct=chain.FLOAT), args, phase))
        inputs.append((self.fixture(4), (proof.S['D_800CC2D0'], 0, 255, proof.PARAMETERS, *outputs), 0))
        for memory, args, phase in inputs:
            original = self.compare(memory, args, phase)[0]
            for ordinal in range(original.accesses):
                failed = []
                for words in (self.original_color, self.color):
                    model = self.color_model(memory, args, words, phase)
                    model.fault = ordinal
                    with self.assertRaises(proof.guest.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args, (ordinal,))
                    self.assertEqual(model.accesses, ordinal)
                    failed.append(model)
                self.assertEqual((failed[0].memory, failed[0].events, failed[0].calls),
                    (failed[1].memory, failed[1].events, failed[1].calls))
                prefixes += 1
        self.receipt('private', aliases=aliases, full_fired_fault_prefix_pairs=prefixes,
            executions=prefixes * 2, original_compiled_full_private_memory_events_calls_exact=True,
            absence_of_fault_is_failure=True)

    def test_04_fresh_effective_complete_color_negatives(self):
        outputs = tuple(COLORS + i * 4 for i in range(10))
        args = (proof.S['D_800CC2D0'], 3, 255, proof.PARAMETERS, *outputs)
        memory = self.fixture(6, 3)
        positive = self.compare(memory, args)[0]
        controls = (('wrong-palette', 'D_800D9B68 +', 'D_800D9B78 +'),
            ('wrong-alpha', '*fogA = parameters[3];', '*fogA = alpha;'),
            ('wrong-gate', 'actor[0xA4] != 0', 'actor[0xA4] == 0'))
        for name, old, new in controls:
            self.assertIn(old, color.SELECTED)
            _, body = color.compile_candidate(self.root, self.out, name, color.SELECTED.replace(old, new))
            selected = self.fixture(0, 3) if name == 'wrong-alpha' else memory
            expected = self.compare(selected, args)[0] if name == 'wrong-alpha' else positive
            wrong = self.color_model(selected, args, body).run()
            self.assertNotEqual({a: value for a, value in wrong.memory.items() if proof.public(a)},
                {a: value for a, value in expected.memory.items() if proof.public(a)}, name)
        self.receipt('negatives', fresh_effective_complete_compiled_color_controls=3,
            unmodified_positives_checked=True)

    def test_05_combined_copied_owner_neighbors_relocations_pools_and_padding(self):
        before = (self.out / 'before-source').read_text()
        objects, diagnostics = [], []
        for name, source in (('owner-before', before), ('owner-after', color.install(before))):
            obj, warnings = compile_owner(self.root, self.out, source, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics, [[], []])
        parsed = [parse_object(obj) for obj in objects]
        def body(data, name):
            text, functions, relocations = data
            function = functions[name]
            return (function['size'], text[function['value']:function['value'] + function['size']],
                {offset - function['value']: uses for offset, uses in relocations.items()
                    if function['value'] <= offset < function['value'] + function['size']})
        self.assertEqual(parsed[0][1].keys(), parsed[1][1].keys())
        targets = (color.FUNCTION, renderer.FUNCTION)
        for name in parsed[0][1]:
            if name not in targets: self.assertEqual(body(parsed[0], name), body(parsed[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(body(parsed[1], color.FUNCTION), body(parse_object(self.out / 'color.o'), color.FUNCTION))
        self.assertEqual(renderer.guard_rows(objects[1]), self.rows)
        guards = self.out / 'qualified-guards.csv'
        guard_bytes = color.guard_bytes((self.out / 'before-guards').read_bytes(), objects[1])
        self.assertTrue(guard_bytes.startswith((self.out / 'before-guards').read_bytes()))
        guards.write_bytes(guard_bytes)
        with guards.open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        with self.assertRaisesRegex(ValueError, 'already installed'):
            color.guard_bytes(guard_bytes, objects[1])
        padded = []
        for index, obj in enumerate(objects):
            name = 'padded-owner-%d' % index
            self.assemble(name, emit_padded_assembly(obj, self.root / 'conker/asm/58F80.s',
                word_patches_path=self.out / 'before-guards' if index == 0 else guards,
                filename='generated_58F80', rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out / (name + '.o')))
        expected = bytearray(padded[0][0])
        for name, words in ((color.FUNCTION, self.original_color), (renderer.FUNCTION, self.original_renderer)):
            target = padded[1][1][name]
            self.assertEqual(target['size'], len(words) * 4)
            first, size = target['value'], target['size']
            expected[first:first + size] = padded[1][0][first:first + size]
        self.assertEqual(bytes(expected), padded[1][0])
        self.receipt('owner', neighbors=len(parsed[0][1]) - 2, diagnostics=0,
            both_complete_bodies_equal_isolated=True, all_other_bodies_relative_relocations_pools_exact=True,
            only_two_target_slots_change=True, color_guards=0, renderer_guards=531)

    def test_06_combined_complete_C_color_renderer_dispatch_connections(self):
        cases = 0
        for kind, view, mode, enabled in itertools.product(range(8), (0, 3), range(7), (0, 1)):
            memory = chain.fixture(view=view, kind=kind, enabled=enabled, count=2)
            args = (proof.OUTPUT, 0, view, mode, 1)
            models = [chain.ConnectedOracle(words, memory, args, self.bodies, self.data,
                caller=True, returns=chain.return_map() if index == 1 else None).run()
                for index, words in enumerate((self.original_renderer, self.raw, self.fitted))]
            for model in models[1:]: self.assertEqual(chain.canonical(model), chain.canonical(models[0]))
            for model in models:
                self.assertIn(color.ENTRY, model.visits)
                captured, call_args = model.render_inputs[0]
                expected, state, _ = chain.reference(captured, call_args)
                self.assertEqual(model.r[2], expected)
                self.assertEqual({a: value for a, value in model.memory.items() if proof.public(a)},
                    {a: value for a, value in state.items() if proof.public(a)})
            cases += 1
        self.receipt('connected', cases=cases, executions=cases * 3,
            complete_compiled_color_and_renderer_with_actual_dispatch_RGB_shading_matrix_fog=True,
            original_fitted_full_memory_order_exact=True, raw_saved_return_PC_adjustment_only=True,
            independent_renderer_public_reference=True, other_callbacks_cosine_bounded=True)

    def test_07_actual_native32_color_and_fog_C_with_live_aliases(self):
        records = []
        standard = tuple(COLORS + i * 4 for i in range(10))
        for kind in range(256):
            records.append((kind, kind % 4, 255, standard, 83, 10.25))
        for kind, index, target in itertools.product(range(8), range(10),
                (COLORS, proof.PARAMETERS + 12, proof.S['D_800CC2D0'] + 0xA4, chain.PRIMITIVE)):
            outputs = list(standard)
            outputs[index] = target
            records.append((kind, 0, -1, outputs, 83, 10.25))
        for direct, amount in itertools.product((0, 1, 254, 255, chain.FLOAT),
                (-100.0, -0.0, 0.0, 0.25, 10.25, 254.9, 255.0, 300.0)):
            records.append((1, 0, 0, standard, direct, amount))
        for view, alpha in itertools.product(range(4), (-2147483648, -1, 0, 1, 254, 255, 256, 2147483647)):
            records.append((0, view, alpha, standard, 83, 10.25))
        serialized = []
        with patch.multiple(proof.guest, read=native.little_read, put=native.little_put), \
                patch.multiple(chain.fog, read=native.little_read, put=native.little_put):
            for kind, view, alpha, outputs, direct, amount in records:
                memory = self.fixture(kind, view, direct, amount)
                args = (proof.S['D_800CC2D0'], view, alpha, proof.PARAMETERS, *outputs)
                expected = reference(memory, args)
                fields = []
                for start, length in ((args[0], 0x32C), (chain.PRIMITIVE, 16), (chain.ENVIRONMENT, 16),
                        (proof.PARAMETERS, 16), (COLORS, 80)):
                    fields.extend(native.image(state, start, length) for state in (memory, expected))
                fields.extend('0x%08XU' % (value & 0xFFFFFFFF) for value in
                    (alpha, view, chain.bits(amount), int(kind == 1 and direct == chain.FLOAT)))
                pointers = []
                for address in outputs:
                    name, offset = next((name, address - base) for name, base, size in
                        (('outputs', COLORS, 80), ('parameters', proof.PARAMETERS, 16),
                         ('actor', args[0], 0x32C), ('D_800D9B68', chain.PRIMITIVE, 16))
                        if base <= address < base + size)
                    pointers.append('(s32 *)(%s+0x%X)' % (name, offset))
                fields.append('{' + ','.join(pointers) + '}')
                serialized.append('{' + ','.join(fields) + '}')
        source = NATIVE_FIXTURE + color.DECLARATIONS + fog_c.SELECTED + '\n' + color.SELECTED + (
            '\nstatic const Case cases[]={\n' + ',\n'.join(serialized) + '\n};\n') + NATIVE_RUNNER + START
        for profile in ('-O2', '-O0'):
            result, detail = self.run_native('native-color-' + profile[1:].lower(), source, profile)
            self.assertEqual(result, 0, (profile, detail))
        controls = []
        for name, old, new in (
                ('native-wrong-palette', 'D_800D9B68 +', 'D_800D9B78 +'),
                ('native-wrong-alpha', '*fogA = parameters[3];', '*fogA = alpha;'),
                ('native-wrong-gate', 'actor[0xA4] != 0', 'actor[0xA4] == 0')):
            self.assertIn(old, color.SELECTED)
            result, detail = self.run_native(name, source.replace(color.SELECTED, color.SELECTED.replace(old, new)))
            self.assertIn(result, (1, 2, 3, 4, 5), (name, result, detail))
            controls.append(dict(name=name, result=result, detail=detail))
        self.receipt('native-color', cases=len(records), profiles=2, executions=len(records) * 2,
            actual_complete_color_and_fog_C=True, explicit_little_endian_independent_reference=True,
            valid_four_views_live_output_parameter_palette_actor_aliases=True,
            finite_pointed_clamps_all_256_modes_and_signed_alphas=True, cosine_bounded=True,
            fresh_effective_complete_native_controls=controls)

    def test_08_whole_linked_installation_and_immutable_guard_history(self):
        hashes = self.baseline
        previous = self.root / 'conker/build/game-actor-renderer-connected-test'
        self.assertEqual(hashes, json.loads((previous / 'baseline.json').read_text()))
        for name in hashes:
            self.assertEqual((self.out / ('before-' + name)).read_bytes(), (previous / ('before-' + name)).read_bytes())
        source = (self.root / color.SOURCE).read_text()
        if color.ORIGINAL in source:
            for name, path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), hashes[name])
            self.receipt('installation', installed=False, immutable_baseline_unchanged=True)
            return
        self.assertEqual(source, color.install((self.out / 'before-source').read_text()))
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith((self.out / 'before-guards').read_bytes()))
        for name in ('progress', 'rodata'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        for function, entry, words in ((color.FUNCTION, color.ENTRY, self.original_color),
                (renderer.FUNCTION, renderer.ENTRY, self.original_renderer)):
            struct.pack_into('>%dI' % len(words), expected, elf_slot_offset(before, entry, len(words) * 4), *words)
            struct.pack_into('>I', expected, elf_symbol_size_offset(before, function), len(words) * 4)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('installation', installed=True, only_two_target_instruction_slots_and_extents_change=True,
            bytes=2328, all_other_linked_bytes_addresses_extents_exact=True,
            guard_prefix_exact=True, added_renderer_guards=531, color_guards=0,
            progress_rodata_exact=True, protected_data=audit)


if __name__ == '__main__':
    unittest.main()
