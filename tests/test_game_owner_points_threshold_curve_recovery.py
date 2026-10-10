"""Complete uninstalled threshold-curve contract and bounded connected evidence."""
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

from tools.experiments import game_owner_points_threshold_curve_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_owner_points_arc_recovery as arc
from tools.tests import test_game_owner_points_initializer_recovery as initializer
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK, native
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools

ACTOR, UPDATE, FALLBACK = 0x20000, 0x151B3184, 0x151B3A7C
EPSILON, STEP = 0x38D1B717, 0x3EB2B8C3
GEOMETRIES = (
    ((0, 0, 0), (0, 9, 0)),
    ((0, 0, 0), (floating(EPSILON), 3, 0)),
    ((0, 0, 0), (floating(EPSILON + 1), 3, 0)),
    ((0, 0, 0), (0, -5, -0.001)),
    ((-30.25, 99.75, -5.5), (100.125, -75.25, 13.75)),
    ((10, -7, 9), (-20, 13, -25)),
    ((0, 0, 0), (4, 3, 0)),
    ((0, 0, 0), (0, 0, 2)),
    ((math.nan, 1, 2), (0, 3, 2)),
    ((math.nan, 1, 2), (0, 3, 5)),
    ((0, 1, 2), (math.inf, 3, 5)),
    ((0, 1, 2), (1e20, -1e20, -1e20)),
)
THRESHOLDS = (-1, -0.0, 0, 1, 6.25, 6.250001, 10, 100, 10000, math.nan, math.inf)


def fixture(index=6, threshold=10, flags=255, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + 7) & 255 for i in range(-0x600, 0x140)}
    memory.update({ACTOR + i: (i * 17 + 0x35) & 255 for i in range(-16, 0x190)})
    for offset, point in zip((0x14, 0x20), GEOMETRIES[index]):
        for axis, value in enumerate(point):
            put(memory, ACTOR + offset + axis * 4, bits(value))
    put(memory, ACTOR + 0x138, bits(threshold))
    memory[ACTOR + 0x10] = flags
    put(memory, symbols['D_800AA3B0'], EPSILON)
    put(memory, symbols['D_800AA3B4'], STEP)
    return memory


def actions_for(symbols=None):
    symbols = symbols or screen.SYMBOLS
    return {0: [(ACTOR + 0x14, bits(999), 4), (ACTOR + 0x138, bits(-999), 4),
                (ACTOR + 0x10, 0xA2, 1), (symbols['D_800AA3B4'], bits(0.125), 4)],
            1: [(symbols['D_800AA3B4'], bits(-0.25), 4)],
            6: [(symbols['D_800AA3B4'], bits(0.75), 4)]}


def reference(memory, symbols=None, actions=None, seed=0, fallback_result=1):
    symbols, actions = symbols or screen.SYMBOLS, actions or {}
    memory, calls, writes = memory.copy(), [], []
    r = arc.rounded

    def load(address):
        return floating(read(memory, address))

    def store(address, value, size=4):
        put(memory, address, value, size)
        writes.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    def call(name, *args):
        index = len(calls)
        calls.append((name, tuple(args) if name == 'func_151B3A7C' else tuple(bits(a) for a in args)))
        for address, value, size in actions.get(index, ()):
            store(address, value, size)
        return fallback_result & 0xFFFFFFFF if name == 'func_151B3A7C' else floating(arc.helper_result(name, index, seed))

    epsilon = load(symbols['D_800AA3B0'])
    first_point = [load(ACTOR + 0x14 + i * 4) for i in range(3)]
    last_point = [load(ACTOR + 0x20 + i * 4) for i in range(3)]
    delta = [r(b - a) for a, b in zip(first_point, last_point)]
    if not (epsilon < abs(delta[0]) or epsilon < abs(delta[2])):
        return memory, calls, writes, 1
    midpoint = [r(a + r(d * 0.5)) for a, d in zip(first_point, delta)]
    first = [r(a - m) for a, m in zip(first_point, midpoint)]
    last = [r(b - m) for b, m in zip(last_point, midpoint)]
    inverse = r(1.0 / r(math.sqrt(r(r(delta[0] * delta[0]) + r(delta[2] * delta[2])))))
    nz, nx = r(delta[2] * inverse), r(delta[0] * inverse)
    projection = r(r(r(last[2] * nz) + r(last[0] * nx)) - r(r(first[2] * nz) + r(first[0] * nx)))
    vertical = r(last[1] - first[1])
    squared = r(r(projection * projection) + r(vertical * vertical))
    length = r(math.sqrt(squared))
    inverse = r(1.0 / length)
    radius = r(length * 0.5)
    threshold = load(ACTOR + 0x138)
    horizontal, upright = r(projection * inverse), r(vertical * inverse)
    quarter = r(squared * 0.25)
    if threshold < quarter:
        return memory, calls, writes, call('func_151B3A7C', ACTOR)
    minor_radius = r(math.sqrt(threshold - quarter))
    angle = 0.0
    for point in range(10):
        sine = call('sinf', angle)
        cosine = call('cosf', angle)
        along, across = r(radius * cosine), r(minor_radius * sine)
        horizontal_value = r(r(along * horizontal) - r(across * upright))
        vertical_value = r(r(along * upright) - r(across * horizontal))
        output = (r(r(horizontal_value * nx) + midpoint[0]), r(vertical_value + midpoint[1]),
                  r(r(horizontal_value * nz) + midpoint[2]))
        for axis, value in enumerate(output):
            store(ACTOR + 0x48 + point * 24 + axis * 4, bits(value))
        angle = r(angle + load(symbols['D_800AA3B4']))
    return memory, calls, writes, 1


class CurveOracle(arc.ArcOracle):
    def __init__(self, words, memory, phase=0, entry=screen.ENTRY, symbols=None, actions=None,
                 seed=0, connected=None, fallback_result=1):
        super().__init__(words, memory, phase=phase, entry=entry, symbols=symbols or screen.SYMBOLS,
            actions=actions, seed=seed, connected=connected)
        self.targets = {v: n for n, v in (symbols or screen.SYMBOLS).items()
            if n in ('func_151B3A7C', 'sinf', 'cosf')}
        self.fallback_result = fallback_result

    def record_call(self, target):
        if target == screen.ENTRY:
            self.invocations.append((target, self.r[4]))
            return
        name = self.targets[target]
        args = (self.r[4],) if name == 'func_151B3A7C' else (self.f[12],)
        self.calls.append((name, args))
        self.events.append(('CALL', name, args))

    def hook(self, target):
        if self.calls[-1][0] != 'func_151B3A7C':
            super().hook(target)
            return
        for address, value, size in self.actions.get(len(self.calls) - 1, ()):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.fallback_result & 0xFFFFFFFF


class GameOwnerPointsThresholdCurveRecoveryTests(unittest.TestCase):
    def run_host(self, body):
        try:
            native.GameRandomCurveRecordTests.run_host(self, body)
        except AssertionError:
            binary = self.path / self._testMethodName
            if binary.exists():
                result = subprocess.run([str(binary)], capture_output=True, timeout=10)
                if len(result.stdout) == 20:
                    raise AssertionError('native case/point/axis/expected/actual: ' +
                        repr(struct.unpack('<5I', result.stdout))) from None
            raise

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-threshold-curve-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>178I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        path = cls.out / 'baseline.json'
        if not path.exists():
            hashes = {}
            for name, relative in cls.paths.items():
                data = (cls.root / relative).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            path.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(path.read_text())
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.coverage, cls.cases = [set(), set()], 0

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, phase=0, symbols=None, actions=None, seed=0, fallback_result=1,
                entry=screen.ENTRY, bodies=None):
        expected, calls, writes, result = reference(memory, symbols, actions, seed, fallback_result)
        models = []
        for i, words in enumerate(bodies or (self.retail, self.words)):
            model = CurveOracle(words, memory, phase, entry, symbols, actions, seed,
                fallback_result=fallback_result).run()
            self.assertEqual(initializer.public(model.memory), initializer.public(expected))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], result)
            self.assertEqual([e for e in model.events if e[0] == 'W' and not STACK - 0x600 <= e[1] < STACK + 0x140], writes)
            if bodies is None:
                self.coverage[i].update(model.visits)
            models.append(model)
        self.cases += 1
        return models

    def test_01_complete_source_shape_and_positive_forms(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (169, 272, 178, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        forms = []
        for name, body in screen.candidates():
            if name.startswith('negative-'):
                continue
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                self.compare(fixture(index, threshold), phase=phase, bodies=(self.retail, words))
            forms.append(meta)
        self.receipt('shape', dict(selected=self.meta, full_positive_forms=forms, retail_words=178,
            retail_frame=280, not_installed=True, guards=0, private_memory_and_scheduling_not_matched=True))

    def test_02_complete_geometry_threshold_flags_and_ABI(self):
        start = self.cases
        for flags, index, threshold, phase in itertools.product((0, 2, 0x80, 255), range(len(GEOMETRIES)),
                THRESHOLDS, (0, 8)):
            self.compare(fixture(index, threshold, flags), phase=phase, seed=flags % 4)
        for visited, length in zip(self.coverage, (178, 169)):
            self.assertEqual(visited, set(range(screen.ENTRY, screen.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=self.cases - start, executions=(self.cases - start) * 2,
            all_original_and_candidate_words_reached=[178, 169], saved_GP_FP_and_SP_preserved=True,
            no_write_fallback_and_twenty_trig_call_paths=True, bounded_trig_not_real_math_bodies=True))

    def test_03_fresh_step_snapshots_and_effective_negatives(self):
        count = 0
        for index, threshold, phase, result in itertools.product((0, 3, 4, 6), (-1, 6.25, 10000),
                (0, 8), (0, 1, 2, 0xFFFFFFFF)):
            self.compare(fixture(index, threshold), phase=phase, actions=actions_for(), fallback_result=result)
            count += 1
        controls = []
        for name, body in screen.candidates():
            if not name.startswith('negative-'):
                continue
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            rejected = False
            for index, threshold in ((6, 10), (6, -1), (4, 10000), (3, 6.25)):
                try:
                    self.compare(fixture(index, threshold), actions=actions_for(), fallback_result=0xFFFFFFFF,
                        bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
            controls.append(name)
        self.receipt('mutations', dict(cases=count, executions=count * 2, effective_compiled_negatives=controls,
            endpoint_threshold_snapshot=True, fresh_angle_step_after_every_point=True,
            fallback_return_not_assumed_to_be_one=True))

    def test_04_actual_native32_complete_source(self):
        cases = []
        for index, threshold, seed, mutate, result in itertools.product(range(8), (-1, 6.25, 10, 10000),
                range(4), (0, 1), (1, 0xFFFFFFFF)):
            memory = fixture(index, threshold, flags=(index * 31) & 255)
            model = CurveOracle(self.retail, memory, seed=seed, actions=actions_for() if mutate else {},
                fallback_result=result).run()
            initial = [read(memory, ACTOR + offset + i * 4) for offset in (0x14, 0x20) for i in range(3)]
            output = [read(model.memory, ACTOR + 0x48 + p * 24 + a * 4) for p in range(10) for a in range(3)]
            args = [a[0] for name, a in model.calls if name != 'func_151B3A7C']
            cases.append((index * 31 & 255, seed, mutate, result, initial, bits(threshold), output,
                model.memory[ACTOR + 0x10], model.r[2], model.calls, args))
        literal = lambda values: '{' + ','.join('0x%08Xu' % v for v in values) + '}'
        entries = ['{%d,%d,%d,0x%08Xu,%s,0x%08Xu,%s,%d,0x%08Xu,%d,%d,%s}' %
            (flags, seed, mutate, ret, literal(input_values), threshold, literal(output_values), final_flags,
             result, len(calls), int(bool(calls) and calls[0][0] == 'func_151B3A7C'), literal(args or [0]))
            for flags, seed, mutate, ret, input_values, threshold, output_values, final_flags, result, calls, args in cases]
        self.fixture = '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
''' + screen.TYPES + '''
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
f32 D_800AA3B0,D_800AA3B4;
struct Case{u32 flags,seed,mutate,fallbackResult,input[6],threshold,output[30],finalFlags,result,count,fallback,args[20];};
static struct Case cases[]={
''' + ',\n'.join(entries) + '''
};
static struct Case *active;static u8 *currentActor;static u32 calls,error;
static void mutation(u32 index){
 if(!active->mutate)return;
 if(index==0){*(u32 *)(currentActor+0x14)=word(999);*(u32 *)(currentActor+0x138)=word(-999);
  currentActor[0x10]=0xA2;D_800AA3B4=0.125f;}
 if(index==1)D_800AA3B4=-0.25f;
 if(index==6)D_800AA3B4=0.75f;
}
static f32 helper(int kind,f32 angle){
 static f32 sine[4]={0.25f,-0.5f,1,-1},cosine[4]={-0.75f,0.5f,-1,1};
 u32 index=calls++;
 if(active->fallback||index>=active->count||word(angle)!=active->args[index]||kind!=(int)(index&1))error=1;
 mutation(index);
 return (kind?cosine:sine)[(index/2+active->seed)%4];
}
f32 sinf(f32 angle){return helper(0,angle);}
f32 cosf(f32 angle){return helper(1,angle);}
f32 fabsf(f32 x){return number(word(x)&0x7FFFFFFFu);}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
s32 func_151B3A7C(u8 *actor){
 if(actor!=currentActor||!active->fallback||calls)error=2;
 mutation(calls++);return (s32)active->fallbackResult;
}
''' + screen.SELECTED + '\n'
        self.run_host('''
union{u32 alignment;u8 bytes[0x1B0];}storage;
u8 *actor=storage.bytes+16,before[0x1B0];u32 i,j,p,a,result,offset;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 active=&cases[i];currentActor=actor;calls=error=0;
 for(j=0;j<sizeof(storage.bytes);j++)storage.bytes[j]=(u8)((j-16)*17+0x35);
 actor[0x10]=(u8)active->flags;
 for(j=0;j<6;j++)*(u32 *)(actor+(j<3?0x14:0x20)+(j%3)*4)=active->input[j];
 *(u32 *)(actor+0x138)=active->threshold;
 for(j=0;j<sizeof(storage.bytes);j++)before[j]=storage.bytes[j];
 D_800AA3B0=number(0x38D1B717u);D_800AA3B4=number(0x3EB2B8C3u);
 result=(u32)func_151B3FDC(actor);
 if(result!=active->result||error||calls!=active->count||actor[0x10]!=active->finalFlags)return 1;
 if(active->mutate&&active->count){
  *(u32 *)(before+16+0x14)=word(999);*(u32 *)(before+16+0x138)=word(-999);before[16+0x10]=0xA2;}
 if(active->count==20)for(p=0;p<10;p++)for(a=0;a<3;a++){
  offset=16+0x48+p*24+a*4;
  if(*(u32 *)(storage.bytes+offset)!=active->output[p*3+a]){
   u32 packet[5]={i,p,a,active->output[p*3+a],*(u32 *)(storage.bytes+offset)};s32 written;
   __asm__ volatile("int $0x80":"=a"(written):"a"(4),"b"(1),"c"(packet),"d"(sizeof(packet)):"memory");
   (void)written;return 2;
  }
  *(u32 *)(before+offset)=active->output[p*3+a];
 }
 for(j=0;j<sizeof(storage.bytes);j++)if(storage.bytes[j]!=before[j])return 3;
}
''')
        self.receipt('native32', dict(cases=len(cases), actual_complete_C=True,
            exact_original_guest_helper_argument_and_output_bits=True, whole_actor_canaries=True,
            bounded_callbacks_and_finite_geometry_not_FCSR_or_original_trig=True))

    def test_05_actual_registration_dispatch_and_real_initializer(self):
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345C0)[0], screen.ENTRY)
        update = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        count = 0
        for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
            memory = fixture(index, threshold, flags=0)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 255
            memory[ACTOR + 0x34] = 2
            put(memory, 0x8008FB00, screen.ENTRY)
            expected, calls, writes, _ = reference(memory)
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(words) * 4, 4), words))
                model = CurveOracle(update, memory, phase=phase, entry=UPDATE, connected=connected).run()
                self.assertEqual(initializer.public(model.memory), initializer.public(expected))
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.invocations, [(screen.ENTRY, ACTOR)])
            count += 1
        init_words = list(struct.unpack_from('>157I', self.rom, 0x1E0F2C))
        actual = sections(self.root / self.paths['elf'])['.game'][1]
        start = sections(self.root / self.paths['elf'])['.game'][0]
        self.assertEqual(actual[FALLBACK - start:FALLBACK - start + 628], struct.pack('>157I', *init_words))
        connected = dict(zip(range(FALLBACK, FALLBACK + 628, 4), init_words))
        for index, phase in itertools.product((3, 4, 6), (0, 8)):
            memory = fixture(index, -1)
            for address in (0x800AA394, 0x800AA398, 0x800AA39C):
                put(memory, address, initializer.SCALE)
            expected = initializer.reference(memory)
            models = [CurveOracle(words, memory, phase=phase, connected=connected).run()
                for words in (self.retail, self.words)]
            for model in models:
                self.assertEqual(initializer.public(model.memory), initializer.public(expected))
                self.assertEqual(model.r[2], 1)
                self.assertEqual(model.calls, [('func_151B3A7C', (ACTOR,))])
        self.receipt('dispatch', dict(complete_original_update_words=81, dispatcher_cases=count,
            actual_registered_pointer='0x8008FB00', complete_original_initializer_words=157,
            real_connected_initializer_cases=6, linked_initializer_exact=True))

    def test_06_original_relocations_and_independent_rebases(self):
        asm = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        self.fragment = begin + asm.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + self.fragment)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(u for group in parse_object(path)[2].values() for u in group)
        self.assertEqual(uses(obj), uses(self.out / 'selected.o'))
        for i, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if i == 0 else {name: (entry & 0xF0000000) + 0x108008 + n * 0x100
                for n, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 178), ('candidate', self.out / 'selected.o', 169)):
                elf = self.out / ('rebase-%d-%s.elf' % (i, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                self.compare(fixture(index, threshold, symbols=symbols), phase=phase, symbols=symbols,
                    entry=entry, bodies=bodies, actions=actions_for(symbols))
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=48, executions=96,
            relocation_uses=sum(uses(obj).values()), semantics_qualify_not_byte_exact=True))

    def test_07_actual_copied_owner_and_unmatched_private_layout(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.OWNER_INSERT +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
        objects = []
        for name, source in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, source, name)
            self.assertEqual(diagnostics, [])
            objects.append(obj)
        old, of, old_rels = parse_object(objects[0])
        new, nf, new_rels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        relative = lambda rels, f: {o - f['value']: uses for o, uses in rels.items()
            if f['value'] <= o < f['value'] + f['size']}
        isolated_text, isolated_functions, isolated_relocations = parse_object(self.out / 'selected.o')
        for name, f in nf.items():
            if name == screen.FUNCTION:
                isolated = isolated_functions[name]
                self.assertEqual(new[f['value']:f['value'] + f['size']],
                    isolated_text[isolated['value']:isolated['value'] + isolated['size']])
                self.assertEqual(relative(new_rels, f), relative(isolated_relocations, isolated))
                continue
            previous = of[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_rels, f)),
                (previous['size'], old[previous['value']:previous['value'] + previous['size']], relative(old_rels, previous)), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        path = self.out / 'padded.s'
        path.write_text(emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
            check=True, capture_output=True)
        _, functions, _ = parse_object(path.with_suffix('.o'))
        target = functions[screen.FUNCTION]
        self.assertEqual((target['size'], functions['func_151B42A4']['value'] - target['value']), (676, 712))
        original = CurveOracle(self.retail, fixture()).run()
        candidate = CurveOracle(self.words, fixture()).run()
        self.assertNotEqual(original.memory, candidate.memory)
        self.assertEqual(initializer.public(original.memory), initializer.public(candidate.memory))
        self.assertNotEqual(self.meta['frame'], 280)
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_equal=True,
            zero_diagnostics=True, actual_padder_slot_bytes=712, candidate_symbol_bytes=676,
            padding_bytes=36, full_private_memory_not_matched=True, installation_rejected=True))

    def test_08_production_baseline_data_registration_unchanged(self):
        for name, relative in self.paths.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), self.baseline[name])
        self.assertIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008FB00 - start)[0], screen.ENTRY)
        for name, value in (('D_800AA3B0', EPSILON), ('D_800AA3B4', STEP)):
            self.assertEqual(struct.unpack_from('>I', data, screen.SYMBOLS[name] - start)[0], value)
        self.receipt('production', dict(baseline=self.baseline, not_installed=True, new_guards=0,
            protected_data=audit, registered_pointer_and_constants_unchanged=True))

    def test_09_public_read_contract_and_private_home_handoff(self):
        models = self.compare(fixture())
        public_reads = lambda model: [e for e in model.events if e[0] == 'R' and not
            STACK - 0x600 <= e[1] < STACK + 0x140]
        expected = Counter({(ACTOR + offset, 4): 1 for offset in (0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x138)})
        expected[(screen.SYMBOLS['D_800AA3B0'], 4)] = 1
        expected[(screen.SYMBOLS['D_800AA3B4'], 4)] = 10
        homes = []
        for model, frame in zip(models, (280, 272)):
            self.assertEqual(Counter((e[1], e[2]) for e in public_reads(model)), expected)
            step_reads, helpers = 0, 0
            last_public_write = None
            for event in model.events:
                if event[0] == 'CALL':
                    helpers += 1
                elif event[0] == 'W' and not STACK - 0x600 <= event[1] < STACK + 0x140:
                    last_public_write = event[1]
                elif event[0] == 'R' and event[1] == screen.SYMBOLS['D_800AA3B4']:
                    self.assertEqual(helpers, (step_reads + 1) * 2)
                    self.assertEqual(last_public_write, ACTOR + 0x50 + step_reads * 24)
                    step_reads += 1
            self.assertEqual(step_reads, 10)
            homes.append(sorted({(e[1] - (STACK - frame), e[2]) for e in model.events if e[0] == 'W'
                and STACK - frame <= e[1] < STACK}))
        self.assertNotEqual(homes[0], homes[1])
        self.assertNotEqual(public_reads(models[0]), public_reads(models[1]))
        self.receipt('reads-homes', dict(original_private_store_offsets=homes[0], candidate_private_store_offsets=homes[1],
            all_six_endpoint_reads_once=True, threshold_read_once_before_helpers=True,
            ten_step_reads_after_point_Z_stores=True, public_read_multisets_equal=True,
            input_read_order_still_different=True, complete_private_memory_not_matched=True))


if __name__ == '__main__':
    unittest.main()
