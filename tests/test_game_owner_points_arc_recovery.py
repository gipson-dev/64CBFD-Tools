"""Complete ten-point arc recovery, helper contracts and uninstalled audits."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_points_arc_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import ActorOracle
from tools.tests.test_game_owner_points_initializer_recovery import public
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK, native
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_state_match import metadata

ACTOR, UPDATE = 0x20000, 0x151B3184
GLOBALS = ('D_800AA3A0', 'D_800AA3A4', 'D_800AA3A8')
VALUES = (0x38D1B717, 0x40490FDB, 0x3EB2B8C3)
GEOMETRIES = (
    ((0, 0, 0), (0, 9, 0)),
    ((0, 0, 0), (floating(VALUES[0]), 3, 0)),
    ((0, 0, 0), (floating(VALUES[0] + 1), 3, 0)),
    ((0, 0, 0), (0, -5, -0.001)),
    ((-30.25, 99.75, -5.5), (100.125, -75.25, 13.75)),
    ((10, -7, 9), (-20, 13, -25)),
    ((-0.0, 0.0, -0.0), (0.0, 0.0, 0.0)),
    ((0, 0, 0), (1e-30, -1e-30, 1e-30)),
    ((math.nan, 1, 2), (0, 3, 2)),
    ((math.nan, 1, 2), (0, 3, 5)),
    ((0, 1, 2), (math.inf, 3, 5)),
    ((0, 1, 2), (1e20, -1e20, -1e20)),
)


def rounded(value):
    return floating(bits(value))


def fixture(index=4, flags=0xFF, actor=ACTOR, symbols=None, values=VALUES):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + 7) & 255 for i in range(-0x600, 0x140)}
    memory.update({actor + i: (i * 17 + 0x35) & 255 for i in range(-16, 0x190)})
    for offset, point in zip((0x14, 0x20), GEOMETRIES[index]):
        for axis, value in enumerate(point):
            put(memory, actor + offset + axis * 4, bits(value))
    memory[actor + 0x10] = flags
    for name, value in zip(GLOBALS, values):
        put(memory, symbols[name], value)
    return memory


def helper_result(name, index, seed):
    if name == 'func_150484A0':
        return bits(0.75 + seed * 0.125)
    values = (0.25, -0.5, 1.0, -1.0) if name == 'sinf' else (-0.75, 0.5, -1.0, 1.0)
    return bits(values[(index // 2 + seed) % len(values)])


def reference(memory, actor=ACTOR, symbols=None, actions=None, seed=0):
    symbols, actions = symbols or screen.SYMBOLS, actions or {}
    memory, calls, writes = memory.copy(), [], []

    def load(address):
        return floating(read(memory, address))

    def store(address, value, size=4):
        put(memory, address, value, size)
        writes.append(('W', address, size, value))

    def call(name, *args):
        index = len(calls)
        calls.append((name, tuple(bits(value) for value in args)))
        for address, value, size in actions.get(index, ()):
            store(address, value, size)
        return floating(helper_result(name, index, seed))

    start = [load(actor + 0x14 + i * 4) for i in range(3)]
    end = [load(actor + 0x20 + i * 4) for i in range(3)]
    delta = [rounded(b - a) for a, b in zip(start, end)]
    threshold = load(symbols['D_800AA3A0'])
    if not (threshold < abs(delta[0]) or threshold < abs(delta[2])):
        return memory, calls, writes
    midpoint = [rounded(a + rounded(d * 0.5)) for a, d in zip(start, delta)]
    first = [rounded(a - m) for a, m in zip(start, midpoint)]
    last = [rounded(b - m) for b, m in zip(end, midpoint)]
    magnitude = rounded(math.sqrt(rounded(rounded(delta[0] * delta[0]) + rounded(delta[2] * delta[2]))))
    inverse = rounded(1.0 / magnitude if magnitude else math.inf)
    nz, nx = rounded(delta[2] * inverse), rounded(delta[0] * inverse)
    projection = rounded(rounded(rounded(last[2] * nz) + rounded(last[0] * nx)) -
        rounded(rounded(first[2] * nz) + rounded(first[0] * nx)))
    vertical = rounded(last[1] - first[1])
    angle = call('func_150484A0', vertical, projection)
    radius = rounded(rounded(math.sqrt(rounded(rounded(projection * projection) + rounded(vertical * vertical)))) * 0.5)
    angle = rounded(angle - load(symbols['D_800AA3A4']))
    step = load(symbols['D_800AA3A8'])
    for point in range(10):
        sine = call('sinf', angle)
        cosine = call('cosf', angle)
        along = rounded(radius * cosine)
        coordinates = (rounded(rounded(along * nx) + midpoint[0]),
            rounded(rounded(radius * sine) + midpoint[1]),
            rounded(rounded(along * nz) + midpoint[2]))
        for axis, value in enumerate(coordinates):
            store(actor + 0x48 + point * 24 + axis * 4, bits(value))
        angle = rounded(angle + step)
    return memory, calls, writes


class ArcOracle(ActorOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, entry=screen.ENTRY,
                 symbols=None, actions=None, seed=0, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=(actor,), connected=connected)
        self.targets = {value: name for name, value in (symbols or screen.SYMBOLS).items()
            if name in ('func_150484A0', 'sinf', 'cosf')}
        self.actions, self.seed, self.invocations = actions or {}, seed, []

    def execute(self, word):
        rs, rd, shift, fn = word >> 21 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if word >> 26 == 17 and rs == 16 and fn in (4, 5):
            value = floating(self.f[rd])
            self.f[shift] = self.f[rd] & 0x7FFFFFFF if fn == 5 else bits(
                math.sqrt(value) if value >= 0 or math.isnan(value) else math.nan)
        else:
            super().execute(word)

    def put(self, address, value, size):
        if self.recording:
            assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        if target == screen.ENTRY:
            self.invocations.append((target, self.r[4]))
            return
        name = self.targets[target]
        args = (self.f[12], self.f[14]) if name == 'func_150484A0' else (self.f[12],)
        self.calls.append((name, args))
        self.events.append(('CALL', name, args))

    def hook(self, target):
        name, _ = self.calls[-1]
        index = len(self.calls) - 1
        result = helper_result(name, index, self.seed)
        for address, value, size in self.actions.get(index, ()):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.f[0] = result


class GameOwnerPointsArcRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'recovered', screen.COMPACT)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>142I', cls.rom, screen.ROM))
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

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, phase=0, entry=screen.ENTRY,
                symbols=None, actions=None, seed=0, bodies=None):
        expected, calls, writes = reference(memory, actor, symbols, actions, seed)
        models = []
        for words in bodies or (self.retail, self.words):
            model = ArcOracle(words, memory, actor, phase, entry, symbols, actions, seed).run()
            self.assertEqual(public(model.memory), public(expected))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], 1)
            actual_writes = [event for event in model.events if event[0] == 'W' and
                not STACK - 0x600 <= event[1] < STACK + 0x140]
            self.assertEqual(actual_writes, writes)
            models.append(model)
        return models

    def test_01_complete_source_profile_and_form_discriminators(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (141, 208, 118, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertNotEqual(self.words, self.retail)
        rows = []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            for index, phase in itertools.product((0, 2, 4, 5), (0, 8)):
                self.compare(fixture(index), phase=phase, bodies=(self.retail, words))
            rows.append(meta)
        for profile in screen.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, screen.COMPACT, profile)
            self.compare(fixture(), bodies=(self.retail, words))
            rows.append(meta)
        self.receipt('shape', dict(selected=self.meta, forms_and_profiles=rows,
            complete_recovery=True, installation_rejected=True, retail_frame=136,
            source_and_control_matching_still_required=True, guards=0))

    def test_02_complete_guest_flags_geometry_and_saved_registers(self):
        coverage = [set(), set()]
        cases = 0
        for flags, index, phase in itertools.product(range(256), (0, 2, 4, 5), (0, 8)):
            for i, model in enumerate(self.compare(fixture(index, flags), phase=phase, seed=flags % 4)):
                coverage[i].update(model.visits)
            cases += 1
        for visited, length in zip(coverage, (142, 141)):
            self.assertEqual(visited, set(range(screen.ENTRY, screen.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=cases, executions=cases * 2, all_flags_preserved=True,
            original_candidate_all_words_reached=[142, 141], saved_GPR_FP_restored=True,
            helper_calls_are_bounded_contracts_not_original_trigonometric_bodies=True))

    def test_03_boundaries_mutation_snapshot_and_effective_negatives(self):
        cases = 0
        actions = {0: [(ACTOR + 0x14, bits(99), 4), (ACTOR + 0x28, bits(-99), 4),
            (screen.SYMBOLS['D_800AA3A4'], bits(-0.5), 4),
            (screen.SYMBOLS['D_800AA3A8'], bits(0.125), 4)],
            1: [(screen.SYMBOLS['D_800AA3A8'], bits(-3), 4), (ACTOR + 0x10, 0xA2, 1)]}
        for index, phase, mutate in itertools.product(range(len(GEOMETRIES)), (0, 8), (False, True)):
            self.compare(fixture(index), phase=phase, actions=actions if mutate else {})
            cases += 1
        mutations = (
            ('return', '    return 1;', '    return 0;'),
            ('count', 'offset != 0xF0', 'offset != 0xD8'),
            ('step', 'angle += angleStep;', 'angle -= angleStep;'),
            ('fresh-step', 'angle += angleStep;', 'angle += D_800AA3A8;'),
            ('arg-order', 'func_150484A0(vertical, projection)', 'func_150484A0(projection, vertical)'),
            ('threshold', 'D_800AA3A0 < fabsf(dx)', 'D_800AA3A0 <= fabsf(dx)'),
            ('position', 'along * nx + midpoint.x', 'along * nz + midpoint.x'),
        )
        for name, old, new in mutations:
            body = screen.COMPACT.replace(old, new)
            self.assertNotEqual(body, screen.COMPACT)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            rejected = False
            for index in (1, 4, 5):
                try:
                    self.compare(fixture(index), actions=actions, bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
        self.receipt('mutations', dict(cases=cases, executions=cases * 2,
            effective_compiled_negatives=len(mutations), threshold_NaN_infinity_and_tiny_cases=True,
            endpoints_midpoint_normalization_snapshot_before_callbacks=True,
            globals_fresh_after_angle_and_step_retained_through_trigonometric_callbacks=True))

    def test_04_actual_native32_source_against_original_guest(self):
        cases = []
        for iteration, seed in itertools.product(range(128), range(4)):
            memory = fixture(iteration % 8, iteration & 255)
            for offset, point in zip((0x14, 0x20), GEOMETRIES[iteration % 8]):
                for axis, value in enumerate(point):
                    put(memory, ACTOR + offset + axis * 4, bits(value + (iteration // 8) * 0.125))
            expected = ArcOracle(self.retail, memory, seed=seed).run()
            initial = [read(memory, ACTOR + offset + i * 4) for offset in (0x14, 0x20) for i in range(3)]
            output = [read(expected.memory, ACTOR + 0x48 + p * 24 + i * 4) for p in range(10) for i in range(3)]
            calls = [list(args) + [0] * (2 - len(args)) for _, args in expected.calls]
            cases.append((iteration & 255, seed, initial, output, calls))
        literal = lambda values: '{' + ','.join('0x%08Xu' % value for value in values) + '}'
        entries = ['{%d,%d,%s,%s,%d,{%s}}' % (flags, seed, literal(initial), literal(output),
            len(calls), ','.join(literal(args) for args in calls) or '{0,0}') for flags, seed, initial, output, calls in cases]
        self.fixture = '''typedef unsigned char u8; typedef unsigned int u32; typedef int s32; typedef float f32;
''' + screen.TYPES + '''
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
f32 D_800AA3A0,D_800AA3A4,D_800AA3A8;
struct Case{u32 flags,seed,input[6],output[30],count,args[21][2];};
static struct Case cases[]={
''' + ',\n'.join(entries) + '''
};
static struct Case *active;static u32 calls,error;
static f32 helper(u32 kind,f32 x,f32 y){
 static f32 sine[4]={0.25f,-0.5f,1,-1},cosine[4]={-0.75f,0.5f,-1,1};
 u32 index=calls++;
 if(index>=active->count||word(x)!=active->args[index][0]||(kind==0&&word(y)!=active->args[index][1]))error=1;
 if((index==0?0:(index&1?1:2))!=kind)error=2;
 return kind==0?0.75f+active->seed*0.125f:(kind==1?sine:cosine)[(index/2+active->seed)%4];
}
f32 func_150484A0(f32 x,f32 y){return helper(0,x,y);}
f32 sinf(f32 x){return helper(1,x,0);}
f32 cosf(f32 x){return helper(2,x,0);}
f32 fabsf(f32 x){return number(word(x)&0x7FFFFFFFu);}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
''' + screen.COMPACT + '\n'
        self.run_host('''
union{u32 alignment;u8 bytes[0x1B0];} storage;
u8 *actor=storage.bytes+16;u8 before[0x1B0];u32 i,j,p,a;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 active=&cases[i];calls=error=0;
 for(j=0;j<sizeof(storage.bytes);j++)storage.bytes[j]=(u8)(j*17+0x35);
 actor[0x10]=(u8)active->flags;
 for(j=0;j<6;j++)*(u32 *)(actor+(j<3?0x14:0x20)+(j%3)*4)=active->input[j];
 for(j=0;j<sizeof(storage.bytes);j++)before[j]=storage.bytes[j];
 D_800AA3A0=number(0x38D1B717u);D_800AA3A4=number(0x40490FDBu);D_800AA3A8=number(0x3EB2B8C3u);
 if(func_151B3CF0(actor)!=1||error||calls!=active->count)return 1;
 if(active->count)for(p=0;p<10;p++)for(a=0;a<3;a++){
  u32 offset=16+0x48+p*24+a*4;
  if(*(u32 *)(storage.bytes+offset)!=active->output[p*3+a])return 2;
  for(j=0;j<4;j++)before[offset+j]=storage.bytes[offset+j];
 }
 for(j=0;j<sizeof(storage.bytes);j++)if(storage.bytes[j]!=before[j])return 3;
}
''')
        self.receipt('native32', dict(cases=len(cases), actual_complete_C=True,
            against_complete_original_guest=True, all_helper_argument_bits_and_actor_canary_bytes=True,
            finite_cases_only=True, no_original_helper_or_FCSR_claim=True))

    def test_05_actual_registered_update_one_argument_dispatch(self):
        update = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345BC)[0], screen.ENTRY)
        cases = 0
        for index, flags, phase in itertools.product((0, 4, 5), (0, 2, 0x80), (0, 8)):
            memory = fixture(index, flags)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 255
            memory[ACTOR + 0x34] = 1
            put(memory, ACTOR + 0x12, 300, 2)
            put(memory, 0x800BE9E4, 1)
            put(memory, 0x8008FAFC, screen.ENTRY)
            expected, calls, _ = reference(memory)
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(words) * 4, 4), words))
                model = ArcOracle(update, memory, phase=phase, entry=UPDATE, connected=connected).run()
                self.assertEqual(public(model.memory), public(expected))
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.invocations, [(screen.ENTRY, ACTOR)])
            cases += 1
        self.receipt('dispatch', dict(cases=cases, executions=cases * 2,
            actual_registered_pointer='0x8008FAFC', complete_original_update_words=81,
            one_argument_success_return_ABI=True))

    def original_fragment(self):
        source = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        return begin + source.split(begin, 1)[1].split(end, 1)[0] + end + '\n'

    def test_06_original_relocations_and_independent_symbol_rebases(self):
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + self.original_fragment())
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 142), ('candidate', self.out / 'recovered.o', 141)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            if index == 0:
                self.assertEqual(bodies, [self.retail, self.words])
            for geometry, phase in itertools.product((0, 2, 4, 5), (0, 8)):
                self.compare(fixture(geometry, symbols=symbols), phase=phase,
                    symbols=symbols, entry=entry, bodies=bodies)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8,
            cases=32, executions=64, relocation_uses=sum(uses(obj).values()), semantic_not_byte_exact=True))

    def test_07_actual_owner_neighbors_and_padding_frame_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.COMPACT)
        objects = []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            self.assertEqual(diagnostics, [])
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        isolated, isolated_functions, isolated_relocations = parse_object(self.out / 'recovered.o')
        isolated_target = isolated_functions[screen.FUNCTION]
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == screen.FUNCTION:
                self.assertEqual(new[function['value']:function['value'] + function['size']],
                    isolated[isolated_target['value']:isolated_target['value'] + isolated_target['size']])
                relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                    if f['value'] <= o < f['value'] + f['size']}
                self.assertEqual(relative(nrels, function), relative(isolated_relocations, isolated_target))
                continue
            previous = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (previous['size'], old[previous['value']:previous['value'] + previous['size']]), name)
            relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                if f['value'] <= o < f['value'] + f['size']}
            self.assertEqual(relative(nrels, function), relative(orels, previous), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        path = self.out / 'padded.s'
        path.write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
            check=True, capture_output=True)
        text, functions, _ = parse_object(path.with_suffix('.o'))
        target = functions[screen.FUNCTION]
        self.assertEqual(target['size'], 564)
        self.assertEqual(functions['func_151B3F28']['value'] - target['value'], 568)
        self.assertEqual(text[target['value'] + 564:target['value'] + 568], bytes(4))
        before_path = self.out / 'padded-before.s'
        before_path.write_text(emit_padded_assembly(objects[0], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(before_path.with_suffix('.o')),
            str(before_path)], check=True, capture_output=True)
        before_text, before_functions, _ = parse_object(before_path.with_suffix('.o'))
        self.assertEqual(before_functions[screen.FUNCTION]['value'], target['value'])
        self.assertEqual(before_text[:target['value']], text[:target['value']])
        self.assertEqual(before_text[target['value'] + 568:], text[target['value'] + 568:])
        self.assertNotEqual(text[target['value']:target['value'] + 568],
            struct.pack('>142I', *self.retail))
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_relative_relocations_preserved=True,
            zero_diagnostics=True, actual_padder_fits_568_byte_slot=True,
            candidate_symbol_bytes=564, remaining_zero_padding_bytes=4,
            all_other_padded_owner_bytes_equal=True,
            installation_rejected_for_frame_and_full_words=True))

    def test_08_production_data_registration_and_progress_unchanged(self):
        hashes = {name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
            for name, path in self.paths.items()}
        self.assertEqual(hashes, self.baseline)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008FAFC - start)[0], screen.ENTRY)
        self.assertIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('preservation', dict(hashes=hashes, protected_data=audit,
            unchanged_production_source_ELF_guards_progress=True, no_installation_or_credit=True))

    def test_09_missing_byte_public_fault_prefixes_and_unused_records(self):
        faults = ((ACTOR + 0x14, 'read'), (ACTOR + 0x28, 'read'),
            (screen.SYMBOLS['D_800AA3A4'], 'read'),
            (screen.SYMBOLS['D_800AA3A8'], 'read'),
            (ACTOR + 0x48, 'store'), (ACTOR + 0x48 + 4 * 24 + 4, 'store'))
        for address, kind in faults:
            memory = fixture()
            del memory[address]
            models = []
            for words in (self.retail, self.words):
                model = ArcOracle(words, memory)
                with self.assertRaisesRegex(AssertionError, 'unmapped ' + kind):
                    model.run()
                models.append(model)
            self.assertEqual(public(models[0].memory), public(models[1].memory))
            self.assertEqual(models[0].calls, models[1].calls)
            writes = lambda model: [event for event in model.events if event[0] == 'W' and
                not STACK - 0x600 <= event[1] < STACK + 0x140]
            self.assertEqual(writes(models[0]), writes(models[1]))
        for address in (ACTOR + 0x11, ACTOR + 0x54):
            memory = fixture()
            del memory[address]
            self.compare(memory)
        self.receipt('faults', dict(missing_byte_faults=len(faults), executions=12,
            public_write_and_call_prefixes_equal=True, unused_byte_cases=2,
            portable_C_fault_and_full_read_order_not_claimed=True))

    def test_10_current_linked_trigonometric_placeholder_boundary(self):
        elf = (self.root / self.paths['elf']).read_bytes()
        symbols = metadata(elf)[2]
        measurements = []
        for name, length, rom in (('cosf', 88, 0x750B0), ('sinf', 104, 0x75210),
                ('func_150484A0', 80, 0x75950)):
            matches = [symbol for symbol in symbols if symbol[0] == name.encode()]
            self.assertEqual(len(matches), 1)
            _, address, size, *_ = matches[0]
            section = next((start, data) for start, data in sections(self.root / self.paths['elf']).values()
                if start <= address and address + length * 4 <= start + len(data))
            start, data = section
            words = list(struct.unpack_from('>%dI' % length, data, address - start))
            original = struct.unpack_from('>%dI' % length, self.rom, rom)
            differences = sum(a != b for a, b in zip(words, original))
            if name in ('sinf', 'cosf'):
                self.assertGreater(differences, 0)
                self.assertEqual(size, 20)
                self.assertEqual(words[:5], [0xE7AC0000, 0x44800000, 0, 0x03E00008, 0])
                for value in (0, bits(1), bits(-1), 0x7FC12345):
                    model = ArcOracle(words[:5], fixture(), entry=address)
                    model.f[12] = value
                    model.run()
                    self.assertEqual(model.f[0], 0)
            else:
                self.assertEqual(differences, 0)
            measurements.append(dict(name=name, linked_symbol_bytes=size,
                retail_words=length, slot_word_differences=differences))
        self.receipt('helpers', dict(measurements=measurements,
            current_linked_sinf_cosf_return_zero=True, zero_return_executions=8,
            original_helper_math_and_live_arc_rendering_not_qualified=True,
            no_helper_source_change=True))


if __name__ == '__main__':
    unittest.main()
