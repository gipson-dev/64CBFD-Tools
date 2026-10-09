"""Complete owner point preparation, ABI, aliases and uninstalled recovery audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_points_initializer_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import ActorOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK, native

ACTOR, UPDATE = 0x20000, 0x151B3184
SCALE = 0x3DE38E39
POINTS = (
    ((0x80000000, 0, 0x3F800000), (0, 0x80000000, 0x3F800000)),
    ((bits(-30.25), bits(99.75), bits(-5.5)), (bits(100.125), bits(-75.25), bits(13.75))),
    ((1, 0x80000001, 0x007FFFFF), (0x00800000, 0x80800000, 1)),
    ((0x7F7FFFFF, 0xFF7FFFFF, 0x3F800000), (0x7F7FFFFF, 0xFF7FFFFF, 0xBF800000)),
)


def fixture(pattern=1, flags=0xFF, actor=ACTOR, scales=(SCALE,) * 3, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + 7) & 255 for i in range(-0x600, 0x140)}
    memory.update({actor + i: (i * 17 + 0x35) & 255 for i in range(-16, 0x190)})
    for i, (first, last) in enumerate(zip(*POINTS[pattern])):
        put(memory, actor + 0x14 + i * 4, first)
        put(memory, actor + 0x20 + i * 4, last)
    memory[actor + 0x10] = flags
    for address, value in zip(symbols.values(), scales):
        put(memory, address, value)
    return memory


def reference(memory, actor=ACTOR, symbols=None):
    symbols = symbols or screen.SYMBOLS
    result = memory.copy()
    position = [read(result, actor + 0x14 + i * 4) for i in range(3)]
    delta = [bits(floating(read(result, actor + 0x20 + i * 4)) - floating(value))
             for i, value in enumerate(position)]
    step = None
    for point in range(10):
        for axis, value in enumerate(position):
            put(result, actor + 0x48 + point * 24 + axis * 4, value)
            put(result, actor + 0x54 + point * 24 + axis * 4, 0)
        if step is None:
            step = [bits(floating(d) * floating(read(result, address)))
                    for d, address in zip(delta, symbols.values())]
        position = [bits(floating(p) + floating(s)) for p, s in zip(position, step)]
    result[actor + 0x10] &= ~2
    return result


def public(values):
    return {a: b for a, b in values.items() if not STACK - 0x600 <= a < STACK + 0x140}


class PointOracle(ActorOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, entry=screen.ENTRY, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
                               arguments=(actor,), connected=connected)
        self.actor = actor

    def get(self, address, size):
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording:
            assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        assert target == screen.ENTRY
        self.calls.append((target, self.r[4]))

    def hook(self, target):
        raise AssertionError(('unexpected external call', target))


class GameOwnerPointsInitializerRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-initializer-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'recovered')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>157I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, result):
        (self.out / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, phase=0, symbols=None, entry=screen.ENTRY, bodies=None):
        expected = reference(memory, actor, symbols)
        models = [PointOracle(words, memory, actor, phase, entry).run()
                  for words in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual(public(model.memory), public(expected))
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.calls, [])
            writes = [e for e in model.events if e[0] == 'W' and not
                      STACK - 0x600 <= e[1] < STACK + 0x140]
            allowed = set(range(actor + 0x48, actor + 0x138)) | {actor + 0x10}
            self.assertTrue(all(set(range(a, a + n)) <= allowed for _, a, n, _ in writes))
        return models

    def test_01_full_shape_profiles_source_forms_and_slot_gate(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
                         (157, 88, 143, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual((-self.retail[0]) & 65535, 96)
        rows = []
        for profile in screen.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.compare(fixture(), bodies=(self.retail, words))
            rows.append(meta)
        forms = []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            failures = []
            for pattern, phase in itertools.product(range(4), (0, 8)):
                try:
                    self.compare(fixture(pattern), phase=phase, bodies=(self.retail, words))
                except AssertionError as error:
                    failures.append(str(error).splitlines()[0])
            forms.append(dict(meta, contract_cases=8, contract_failures=failures))
        self.receipt('shape', dict(selected=self.meta, profiles=rows, forms=forms,
            installation_rejected=True, frame_and_private_home_mismatch=True, guards=0))

    def test_02_flags_geometry_all_words_and_saved_registers(self):
        coverage = [set(), set()]
        for flags, pattern, phase in itertools.product(range(256), range(4), (0, 8)):
            for index, model in enumerate(self.compare(fixture(pattern, flags), phase=phase)):
                coverage[index].update(model.visits)
        self.assertEqual(coverage[0], set(range(screen.ENTRY, screen.ENTRY + 628, 4)))
        self.assertEqual(coverage[1], set(range(screen.ENTRY, screen.ENTRY + len(self.words) * 4, 4)))
        self.receipt('guest', dict(cases=2048, executions=4096, retail_words_reached=157,
            candidate_words_reached=len(self.words), all_flag_bytes=True, private_trace_not_matching=True,
            saved_GPR_and_FP_restored=True, no_hardware_FCSR_claim=True))

    def test_03_independent_scales_aliases_and_effective_negatives(self):
        cases = 0
        for scales, pattern, phase in itertools.product(
                ((SCALE,) * 3, (bits(1.), bits(-1.), 0), (1, 0x80000001, bits(2.)),
                 (bits(0.25), bits(-0.5), bits(4.))), range(4), (0, 8)):
            self.compare(fixture(pattern, scales=scales), phase=phase)
            cases += 1
        # Input constants can alias the first output record; load after its stores.
        for actor, pattern in itertools.product(
                (0x800AA394 - 0x48, 0x800AA394 - 0x54, 0x800AA394 - 0x50), range(4)):
            self.compare(fixture(pattern, actor=actor), actor=actor)
            cases += 1
        negatives = (
            screen.RECOVERED.replace('actor[0x10] &= ~2;', 'actor[0x10] |= 2;'),
            screen.RECOVERED.replace('return 1;', 'return 0;'),
            screen.RECOVERED.replace('count = 10;', 'count = 6;'),
            screen.RECOVERED.replace('position.x += step.x;', 'position.x -= step.x;'),
            screen.RECOVERED.replace('step.z = delta.z * D_800AA39C;', 'step.z = delta.z * D_800AA394;'),
            screen.RECOVERED.replace('points[0].velocity.z = 0.0f;', 'points[0].velocity.z = 1.0f;'),
        )
        for i, body in enumerate(negatives):
            self.assertNotEqual(body, screen.RECOVERED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-%d' % i, body)
            with self.assertRaises(AssertionError):
                self.compare(fixture(scales=(bits(.25), bits(-.5), bits(2.))), bodies=(words,))
        self.receipt('mutations', dict(cases=cases, executions=cases * 2,
            first_record_constant_aliases=True, effective_compiled_negatives=len(negatives)))

    def test_04_actual_native32_source_and_complete_actor_bytes(self):
        self.fixture = '''
typedef unsigned int u32; typedef int s32; typedef unsigned char u8; typedef float f32;
''' + screen.TYPES + '''
f32 D_800AA394, D_800AA398, D_800AA39C;
static u8 storage[0x1B0] __attribute__((aligned(16)));
static u32 word(f32 x) { union { f32 f; u32 u; } v; v.f=x; return v.u; }
static f32 number(u32 x) { union { f32 f; u32 u; } v; v.u=x; return v.f; }
''' + screen.RECOVERED + '\n'
        self.run_host("""
int flag,seed,axis,point,k; u8 *actor=storage+16;
u32 expected[10][3]; u8 before[0x1B0]; f32 p[3],step[3],end[3],scale[3];
for(flag=0;flag<256;flag++) for(seed=0;seed<32;seed++) {
    for(k=0;k<0x1B0;k++) storage[k]=(u8)(k*17+seed*13+0x35);
    actor[0x10]=(u8)flag;
    for(axis=0;axis<3;axis++) {
        p[axis]=(f32)(seed*31-axis*7-99)*0.125f;
        end[axis]=(f32)(seed*-19+axis*23+100)*0.25f;
        scale[axis]=(seed&1)?number(0x3DE38E39):(f32)(axis-1)*0.25f;
        *(f32 *)(actor+0x14+axis*4)=p[axis];
        *(f32 *)(actor+0x20+axis*4)=end[axis];
        step[axis]=(end[axis]-p[axis])*scale[axis];
    }
    D_800AA394=scale[0]; D_800AA398=scale[1]; D_800AA39C=scale[2];
    for(k=0;k<0x1B0;k++) before[k]=storage[k];
    for(point=0;point<10;point++) for(axis=0;axis<3;axis++) {
        expected[point][axis]=word(p[axis]); p[axis]+=step[axis];
    }
    if(func_151B3A7C(actor)!=1 || actor[0x10]!=(u8)(flag&~2)) return 1;
    for(point=0;point<10;point++) for(axis=0;axis<3;axis++) {
        if(word(*(f32 *)(actor+0x48+point*24+axis*4))!=expected[point][axis]) return 2;
        if(word(*(f32 *)(actor+0x54+point*24+axis*4))) return 3;
    }
    for(k=0;k<0x1B0;k++) if(k!=16+0x10 && !(16+0x48<=k && k<16+0x138)
        && before[k]!=storage[k]) return 4;
}
""")
        self.receipt('native32', dict(cases=8192, actual_complete_C=True,
            finite_binary32=True, all_actor_and_canary_bytes=True, no_FCSR_claim=True))

    def test_05_actual_registered_update_dispatch_and_return(self):
        update = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345B8)[0], screen.ENTRY)
        for pattern, flags, phase in itertools.product(range(4), (0, 2, 0x80, 0x83), (0, 8)):
            memory = fixture(pattern, flags)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 255
            memory[ACTOR + 0x34] = 0
            put(memory, ACTOR + 0x12, 300, 2)
            put(memory, 0x800BE9E4, 1)
            put(memory, 0x8008FAF8, screen.ENTRY)
            expected = reference(memory)
            if flags & 1:
                put(expected, ACTOR + 0x12, 299, 2)
            models = []
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(words) * 4, 4), words))
                model = PointOracle(update, memory, phase=phase, entry=UPDATE, connected=connected).run()
                self.assertEqual(public(model.memory), public(expected))
                self.assertEqual(model.calls, [(screen.ENTRY, ACTOR)])
                models.append(model)
            self.assertEqual(models[0].calls, models[1].calls)
        self.receipt('dispatch', dict(cases=32, executions=64, actual_complete_update_words=81,
            actual_registered_one_argument_ABI=True, callback_return_success=True,
            full_walker_and_cleanup_outside_scope=True))

    def test_06_original_relocations_and_independent_rebases(self):
        owner = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        original = begin + owner.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + original)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        cases = 0
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {
                name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path in (('original', obj), ('candidate', self.out / 'recovered.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                    '-o', str(elf), str(path)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>157I', sections(elf)['.text'][1])))
            if index == 0:
                self.assertEqual(bodies[0], self.retail)
                self.assertEqual(bodies[1], self.words)
            for pattern, phase in itertools.product(range(4), (0, 8)):
                self.compare(fixture(pattern, symbols=symbols), symbols=symbols,
                    phase=phase, entry=entry, bodies=bodies)
                cases += 1
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=cases,
            executions=cases * 2, relocation_uses=sum(uses(obj).values()),
            semantic_not_byte_exact=True))

    def test_07_actual_owner_neighbors_padder_and_frame_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.TYPES.split('\n', 1)[1] +
            screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(
            screen.ORIGINAL, screen.RECOVERED)
        objects, warnings = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings, [[], []])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                if f['value'] <= o < f['value'] + f['size']}
            self.assertEqual(relative(nrels, function), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, fs, _ = parse_object(self.out / 'recovered.o')
        target = nf[screen.FUNCTION]
        self.assertEqual(target['size'], 628)
        self.assertEqual(new[target['value']:target['value'] + 628],
                         isolated[fs[screen.FUNCTION]['value']:fs[screen.FUNCTION]['value'] + 628])
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        (self.out / 'padded.s').write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(self.out / 'padded.o'),
            str(self.out / 'padded.s')], check=True, capture_output=True)
        self.assertNotEqual(self.meta['frame'], 96)
        self.receipt('owner', dict(neighbors=len(nf) - 1, existing_warnings=0, new_warnings=0,
            pools_and_relative_relocations_preserved=True, slot_fits_actual_padder=True,
            installation_rejected_frame_private_homes_and_words=True))

    def test_08_production_baseline_data_and_registration_unchanged(self):
        current = {name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                   for name, path in self.paths.items()}
        self.assertEqual(current, self.baseline)
        source = (self.root / screen.SOURCE).read_text()
        self.assertEqual(source.count(screen.ORIGINAL), 1)
        self.assertNotIn(screen.RECOVERED, source)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008FAF8 - start)[0], screen.ENTRY)
        for i, address in enumerate(screen.SYMBOLS.values()):
            self.assertEqual(struct.unpack_from('>I', data, address - start)[0], SCALE)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('preservation', dict(installed=False, hashes=current, protected_data=audit,
            actual_registered_pointer='0x8008FAF8', no_new_guards_or_matching_credit=True))

    def test_09_missing_byte_public_prefixes_and_unused_bytes(self):
        faults = (ACTOR + 0x20, ACTOR + 0x48, 0x800AA394, ACTOR + 0x10)
        for address in faults:
            memory = fixture()
            memory.pop(address)
            models = [PointOracle(words, memory) for words in (self.retail, self.words)]
            for model in models:
                with self.assertRaisesRegex(AssertionError, 'unmapped (read|store)'):
                    model.run()
            self.assertEqual(public(models[0].memory), public(models[1].memory))
            self.assertEqual(models[0].calls, models[1].calls)
        for address in (ACTOR + 0x3C, ACTOR + 0x14C):
            memory = fixture()
            memory.pop(address)
            self.compare(memory)
        self.receipt('faults', dict(missing_byte_cases=4, fault_executions=8,
            unused_byte_cases=2, unused_executions=4, public_memory_prefix_equal=True,
            read_order_private_trace_and_hardware_exceptions_not_claimed=True))
