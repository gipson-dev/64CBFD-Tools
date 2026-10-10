"""Complete 14-argument metadata adapter, physical homes and connected retail helpers."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_metadata_adapter_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_points_initializer_recovery as initial
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests import test_game_random_curve_record as native

from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import ActorOracle
from tools.tests import test_game_owner_ribbon_renderer_recovery as renderer

ACTOR, OBJECT, ALTERNATE, OUTPUT = 0x20000, 0x22000, 0x23000, 0x24000
HELPER, DEFAULT, COS, TABLE = 0x1502EC34, 0x151B498C, 0x15047C00, 0x8008FB14
VALUES = ((1, 2, 3, 4), (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x12345678),
    (255, 256, 257, 0x800001FF), (0, 0, 0, 0))
RETURNS = (0, 1, 2, 255, 256, 257, 0x80000000, 0xFFFFFFFF)
ARGUMENTS = (ACTOR, *(OUTPUT + i * 4 for i in range(11)), OUTPUT + 44, OUTPUT + 45)


def fixture(mode=1, seed=0):
    memory = {STACK + i: (i * 13 + seed * 19 + 7) & 255 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR, 0x190), (OBJECT, 0x180), (ALTERNATE, 0x180), (OUTPUT, 80)):
        memory.update({base + i: (i * 17 + seed * 13 + 0x35) & 255 for i in range(size)})
    initial.put(memory, ACTOR + 0x150, OBJECT)
    memory[OBJECT + 0xA4] = mode
    memory[ALTERNATE + 0xA4] = mode ^ 1
    return memory


def public(memory):
    return {a: b for a, b in memory.items() if not STACK - 0x600 <= a < STACK + 0x140}


def default_writes(memory, arguments):
    values = (0x220005, 0x40600, *(255 for _ in range(8)), 0, 5, 0x2B)
    for i, (address, value) in enumerate(zip(arguments[1:], values)):
        initial.put(memory, address, value, 4 if i < 11 else 1)


def reference(memory, arguments=ARGUMENTS, phase=0, values=VALUES[0], actions=(), fallback=1):
    result = memory.copy()
    sp = STACK + phase
    for i, value in enumerate(arguments):
        initial.put(result, sp + i * 4 if i < 4 else sp + 0x10 + (i - 4) * 4, value)
    initial.put(result, sp - 0x2C, 0xDEAD0000)
    result[sp - 1] = 1
    object_address = initial.read(result, arguments[0] + 0x150)
    initial.put(result, sp - 0x10, object_address)
    initial.put(result, sp - 0x58, sp - 0x20)
    outputs = tuple(sp - offset for offset in (0x14, 0x18, 0x1C, 0x20))
    calls = [(HELPER, object_address, *outputs)]
    for address, value in zip(outputs, values): initial.put(result, address, value)
    for address, value, size in actions: initial.put(result, address, value, size)
    captured = initial.read(result, sp - 0x10)
    status = result[sp - 1]
    first = tuple(initial.read(result, sp + i * 4) for i in range(4))
    if result[captured + 0xA4] & 1:
        initial.put(result, first[1], 0x200005)
        initial.put(result, first[2], 0x60600)
        initial.put(result, first[3], initial.read(result, outputs[0]))
        def pointer(index):
            return initial.read(result, sp + 0x10 + (index - 4) * 4)
        for index, local in ((4, outputs[1]), (5, outputs[2])):
            address = pointer(index)
            initial.put(result, address, initial.read(result, local))
        initial.put(result, pointer(6), 255)
        opacity = initial.read(result, outputs[3])
        for index in (9, 8, 7): initial.put(result, pointer(index), opacity)
        initial.put(result, pointer(10), 255)
        initial.put(result, pointer(11), 0x100000)
        initial.put(result, pointer(12), 5, 1)
        initial.put(result, pointer(13), 0x2F, 1)
    else:
        rest = tuple(initial.read(result, sp + 0x10 + i * 4) for i in range(10))
        for i, value in enumerate(rest): initial.put(result, sp - 0x58 + i * 4, value)
        args = first + rest
        calls.append((DEFAULT, *args))
        default_writes(result, args)
        status = fallback & 255
    return result, calls, status


class AdapterOracle(ActorOracle):
    def __init__(self, words, memory, arguments=ARGUMENTS, phase=0, values=VALUES[0],
            actions=(), fallback=1, entry=screen.ENTRY, connected=None, symbols=None, cosine=0x3F800000):
        TriangleOracle.__init__(self, words, memory, arguments=arguments, phase=phase,
            entry=entry, connected=connected)
        self.values, self.actions, self.fallback = values, actions, fallback
        self.symbols = symbols or screen.SYMBOLS
        self.cosine = cosine

    def get(self, address, size):
        assert address % size == 0 and all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording:
            assert address % size == 0 and all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        counts = {self.symbols['func_1502EC34']: 5, self.symbols['func_151B498C']: 14, COS: 0}
        assert target in counts, ('unexpected adapter call', target)
        args = (self.f[12],) if target == COS else tuple(self.arguments(counts[target]))
        self.calls.append((target, *args))

    def hook(self, target):
        if target == self.symbols['func_1502EC34']:
            for address, value in zip(self.arguments(5)[1:], self.values): self.put(address, value, 4)
            for address, value, size in self.actions: self.put(address, value, size)
        elif target == self.symbols['func_151B498C']:
            values = (0x220005, 0x40600, *(255 for _ in range(8)), 0, 5, 0x2B)
            for i, (address, value) in enumerate(zip(self.arguments(14)[1:], values)):
                self.put(address, value, 4 if i < 11 else 1)
        else:
            assert target == COS
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.fallback & 0xFFFFFFFF
        self.f[0] = self.cosine


class GameOwnerMetadataAdapterMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-metadata-adapter-test'
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.fitted = screen.recipe(cls.raw)[0]
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>89I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(baseline.read_text())
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        cls.rows = screen.guard_rows(cls.out / 'selected.o')
        assert not any(row['function'] == screen.FUNCTION for row in cls.old_rows)
        cls.guards = cls.out / 'qualified-guards.csv'
        for path, rows in ((cls.guards, cls.old_rows + cls.rows), (cls.out / 'isolated-guards.csv', cls.rows)):
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        asm = (cls.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        cls.fragment = begin + asm.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        (cls.out / 'slot.s').write_text(cls.fragment)
        (cls.out / 'original.s').write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + cls.fragment)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.out / 'original.o'), str(cls.out / 'original.s')], cwd=cls.root, check=True, capture_output=True)
        (cls.out / 'fitted.s').write_text(emit_padded_assembly(cls.out / 'selected.o', cls.out / 'slot.s',
            word_patches_path=cls.out / 'isolated-guards.csv', filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.out / 'fitted.o'), str(cls.out / 'fitted.s')], check=True, capture_output=True)
        cls.coverage, cls.cases = [set(), set(), set()], 0
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

        cls.fixture = '''typedef unsigned char u8; typedef unsigned int u32;
typedef int s32;
/* The actual selected body retains three unaccessed retail padding words. */
#pragma GCC diagnostic ignored "-Wunused-variable"
static u8 storage[0x800] __attribute__((aligned(16)));
static u8 expected[0x800] __attribute__((aligned(16)));
static u8 *owner, *object, *alternate;
static s32 *outputs[11];
static u8 *bankOut, *combineOut;
static s32 callbackValues[4];
static u32 fallbackResult;
static int mutation, errors, helpers, defaults;
static void reset(int mode,int seed,int change,int alias){
    int i;for(i=0;i<0x800;i++)storage[i]=(u8)(i*17+seed*13+0x35);
    owner=storage+16;object=storage+0x200;alternate=storage+0x380;
    *(u8 **)(owner+0x150)=object;object[0xA4]=(u8)mode;alternate[0xA4]=(u8)(mode^1);
    for(i=0;i<11;i++)outputs[i]=(s32 *)(storage+(alias<0?0x600+i*4:alias));
    bankOut=storage+(alias<0?0x62C:alias);combineOut=bankOut+1;
    callbackValues[0]=(s32)0x800001FF;callbackValues[1]=-1;
    callbackValues[2]=0x12345678;callbackValues[3]=(s32)0x87654321;
    fallbackResult=0x102;mutation=change;errors=helpers=defaults=0;
}
void func_1502EC34(u8 *captured,s32 *r,s32 *g,s32 *b,s32 *a){
    if(captured!=object)errors++;
    helpers++;*r=callbackValues[0];*g=callbackValues[1];*b=callbackValues[2];*a=callbackValues[3];
    if(mutation&1)captured[0xA4]^=1;
    if(mutation&2)*(u8 **)(owner+0x150)=alternate;
}
''' + screen.DECLARATIONS + '''
s32 func_151B498C(''' + screen.SIGNATURE + '''){
    defaults++;if(owner!=storage+16)errors++;
    *mode1=0x220005;*mode2=0x40600;
    *envR=*envG=*envB=*alpha=*primR=*primG=*primB=*primA=255;
    *renderMode=0;*bank=5;*combine=0x2B;return (s32)fallbackResult;
}
static int expectedResult;
static void reference(void){
    int i;u8 *captured; s32 *p[11];u8 *bank,*combine;
    for(i=0;i<0x800;i++)expected[i]=storage[i];
    captured=expected+0x200;
    if(mutation&1)captured[0xA4]^=1;
    if(mutation&2)*(u8 **)(expected+16+0x150)=alternate;
    for(i=0;i<11;i++)p[i]=(s32 *)(expected+((u8 *)outputs[i]-storage));
    bank=expected+(bankOut-storage);combine=expected+(combineOut-storage);
    if(captured[0xA4]&1){
        *p[0]=0x200005;*p[1]=0x60600;
        *p[2]=callbackValues[0];*p[3]=callbackValues[1];*p[4]=callbackValues[2];
        *p[5]=255;*p[8]=callbackValues[3];*p[7]=callbackValues[3];*p[6]=callbackValues[3];
        *p[9]=255;*p[10]=0x100000;*bank=5;*combine=0x2F;expectedResult=1;
    }else{
        *p[0]=0x220005;*p[1]=0x40600;
        for(i=2;i<10;i++)*p[i]=255;
        *p[10]=0;*bank=5;*combine=0x2B;expectedResult=fallbackResult&255;
    }
}
static int invoke(void){
    return func_151B4A14(owner,outputs[0],outputs[1],outputs[2],outputs[3],outputs[4],
        outputs[5],outputs[6],outputs[7],outputs[8],outputs[9],outputs[10],bankOut,combineOut);
}
''' .replace('static int invoke(void){', 's32 func_151B4A14(' + screen.SIGNATURE + ');\nstatic int invoke(void){') + screen.SELECTED + '\n'

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, arguments=ARGUMENTS, phase=0, values=VALUES[0], actions=(), fallback=1,
            bodies=None, entry=screen.ENTRY, symbols=None):
        expected, calls, status = reference(memory, arguments, phase, values, actions, fallback)
        if symbols:
            calls = [(symbols.get('func_1502EC34' if c[0] == HELPER else 'func_151B498C'), *c[1:]) for c in calls]
        models = [AdapterOracle(words, memory, arguments, phase, values, actions, fallback,
            entry=entry, symbols=symbols).run() for words in bodies or (self.retail, self.raw, self.fitted)]
        for model in models:
            self.assertEqual(model.memory, expected)
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], status)
        if len(models) > 1:
            for model in models[1:]: self.assertEqual(model.events, models[0].events)
        if bodies is None:
            for i, model in enumerate(models): self.coverage[i].update(model.visits)
        self.cases += 1
        return models

    def test_01_complete_shape_frame_homes_and_closed_recipe(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (89, 104, 15, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(len(self.rows), 89)
        self.assertTrue(all(row['omit'] == 'false' for row in self.rows))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345D4)[0], screen.ENTRY)
        self.receipt('shape', dict(raw=self.meta, normalized_words=89, normalized_differences=0,
            guards=89, changed_words=15, dependency_words=74, frame=104,
            original_physical_homes_preserved=True, no_padding_or_omissions=True))

    def test_02_all_modes_callback_values_flags_and_complete_memory(self):
        start = self.cases
        for mode, pattern, phase in itertools.product(range(256), range(4), (0, 8)):
            for mutation in ((), ((OBJECT + 0xA4, mode ^ 1, 1),),
                    ((ACTOR + 0x150, ALTERNATE, 4),),
                    ((OBJECT + 0xA4, mode ^ 1, 1), (ACTOR + 0x150, ALTERNATE, 4))):
                self.compare(fixture(mode, pattern), phase=phase, values=VALUES[pattern],
                    actions=mutation, fallback=RETURNS[mode % len(RETURNS)])
        for reached in self.coverage:
            self.assertEqual(reached, set(range(screen.ENTRY, screen.ENTRY + 356, 4)))
        self.receipt('matrix', dict(cases=self.cases - start, executions=(self.cases - start) * 3,
            all_mode_bytes=True, callback_mutations=4, complete_memory_and_full_events_equal=True,
            all_89_words_reached=True, return_truncated_and_original_frame_homes=True))

    def test_03_output_aliases_private_status_and_effective_full_negatives(self):
        start = self.cases
        for mode, phase in itertools.product((0, 1, 2, 3, 254, 255), (0, 8)):
            for address in (OUTPUT, OBJECT + 0xA4, ACTOR + 0x150, STACK + phase - 0x14, STACK + phase - 0x20):
                args = (ACTOR, *(address for _ in range(11)), address, address + 1)
                self.compare(fixture(mode), args, phase, VALUES[1])
            self.compare(fixture(mode), phase=phase,
                actions=((STACK + phase - 1, 0xFF, 1),), fallback=0xFFFFFFFF)
        negatives = {
            'negative-early-mode': (fixture(1), ARGUMENTS, ((OBJECT + 0xA4, 0, 1),), 1),
            'negative-reload-object': (fixture(1), ARGUMENTS, ((ACTOR + 0x150, ALTERNATE, 4),), 1),
            'negative-byte-color': (fixture(1), ARGUMENTS, (), 1),
            'negative-wrong-custom': (fixture(1), ARGUMENTS, (), 1),
            'negative-store-order': (fixture(1), (ACTOR, OUTPUT, OUTPUT, *ARGUMENTS[3:]), (), 1),
            'negative-wide-return': (fixture(2), ARGUMENTS, (), 0x102),
        }
        count = 0
        for name, body in screen.candidates():
            if name not in negatives: continue
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            memory, args, actions, result = negatives[name]
            good = AdapterOracle(self.retail, memory, args, values=VALUES[1], actions=actions, fallback=result).run()
            bad = AdapterOracle(words, memory, args, values=VALUES[1], actions=actions, fallback=result).run()
            self.assertNotEqual((public(good.memory), good.r[2]), (public(bad.memory), bad.r[2]), name)
            count += 1
        self.assertEqual(count, 6)
        self.receipt('aliases', dict(cases=self.cases - start, effective_full_compiled_negatives=count,
            output_to_output_object_owner_pointer_and_private_local_aliases=True,
            callback_status_byte_mutation_qualified=True))

    def test_04_every_private_and_public_fault_prefix_and_unused_words(self):
        cases = 0
        for mode, phase in itertools.product((1, 2), (0, 8)):
            good = AdapterOracle(self.retail, fixture(mode), phase=phase).run()
            addresses = {(e[1], e[2]) for e in good.events if e[0] in ('R', 'W')}
            for address, size in addresses:
                outcomes = []
                for words in (self.retail, self.raw, self.fitted):
                    model = AdapterOracle(words, fixture(mode), phase=phase)
                    for i in range(size): model.memory.pop(address + i, None)
                    with self.assertRaises(AssertionError): model.run()
                    outcomes.append((model.memory, model.events))
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(outcomes[0], outcomes[2])
                cases += 1
            memory = fixture(mode)
            for offset in (-0x24, -0xC, -8):
                for i in range(4): del memory[STACK + phase + offset + i]
            self.compare(memory, phase=phase)
        self.receipt('faults', dict(paired_three_body_fault_prefixes=cases,
            frame_private_and_argument_homes_included=True, three_reserved_words_unmapped_and_untouched=True,
            guest_not_portable_C_or_hardware_fault_claim=True))

    def test_05_actual_native32_full_C_widths_mutations_and_aliases(self):
        self.run_host('''
int mode,seed,change,alias,i,result;static int aliases[]={-1,0x600,0x2A4,0x160};
if(sizeof(void *)!=4 || sizeof(s32)!=4)return 1;
for(mode=0;mode<256;mode++)for(seed=0;seed<8;seed++)for(change=0;change<4;change++){
    reset(mode,seed,change,-1);reference();result=invoke();
    if(result!=expectedResult || errors || helpers!=1 || defaults!=!((mode^change)&1))return 2;
    for(i=0;i<0x800;i++)if(storage[i]!=expected[i])return 3;
}
for(mode=0;mode<256;mode++)for(alias=0;alias<4;alias++)for(change=0;change<4;change++){
    reset(mode,alias,change,aliases[alias]);reference();result=invoke();
    if(result!=expectedResult || errors || helpers!=1 || defaults!=!((mode^change)&1))return 4;
    for(i=0;i<0x800;i++)if(storage[i]!=expected[i])return 5;
}
''')
        self.receipt('native32', dict(actual_full_C=True, finite_full_memory_cases=8192,
            output_alias_cases=4096, fourteen_argument_ABI=True, unsigned_byte_return=True,
            hostile_helper_object_mode_mutations=True, no_private_fault_or_hardware_claim=True))

    def test_06_independent_JAL_rebases_and_complete_original_mode_helper(self):
        cases = 0
        for index, (entry, helper, default) in enumerate(((screen.ENTRY, HELPER, DEFAULT),
                (0x15208000, 0x15198004, 0x15307FFC), (0x15307FF0, 0x15137FFC, 0x15418000),
                (0x15417FFC, 0x15248000, 0x15368004))):
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            symbols = dict(func_1502EC34=helper, func_151B498C=default)
            bodies = []
            for label in ('original', 'selected', 'fitted'):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf),
                    str(self.out / (label + '.o'))], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>89I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[2])
            for mode, phase in itertools.product((0, 1, 2, 255), (0, 8)):
                self.compare(fixture(mode), phase=phase, bodies=bodies, entry=entry, symbols=symbols)
                cases += 1
        helper_words = list(struct.unpack_from('>150I', self.rom, 0x5C0E4))
        default_words = list(struct.unpack_from('>34I', self.rom, 0x1E1E3C))
        cases_connected = 0
        for mode, opacity, cosine, phase in itertools.product((0, 1, 2, 3, 4, 5, 6, 7, 254, 255),
                (127, bits(-4), bits(10.25), bits(300)), (bits(-1), bits(0), bits(1)), (0, 8)):
            memory = fixture(mode)
            memory.update({0x25000 + i: 0 for i in range(4)})
            initial.put(memory, 0x25000, opacity)
            initial.put(memory, OBJECT + 0xA0, 127 if opacity == 127 else 0x25000)
            memory[OBJECT + 0xA5], memory[OBJECT + 0xA6], memory[OBJECT + 0xA7] = 37, 52, 71
            for i, value in enumerate(struct.unpack_from('>9I', self.rom, 0x23B9DC)):
                initial.put(memory, 0x80096F1C + i * 4, value)
            outcomes = []
            for words in (self.retail, self.raw, self.fitted):
                connected = dict(zip(range(HELPER, HELPER + 600, 4), helper_words))
                connected.update(zip(range(DEFAULT, DEFAULT + 136, 4), default_words))
                model = AdapterOracle(words, memory, phase=phase, connected=connected, cosine=cosine).run()
                outcomes.append((model.memory, model.events, model.calls, model.r[2]))
                self.assertTrue(set(range(screen.ENTRY, screen.ENTRY + 24, 4)) <= model.visits)
                self.assertTrue(any(HELPER <= address < HELPER + 600 for address in model.visits))
                self.assertEqual(model.r[2], 1)
            self.assertEqual(outcomes[0], outcomes[1])
            self.assertEqual(outcomes[0], outcomes[2])
            cases_connected += 1
        self.receipt('rebases-connected', dict(independent_links=12, symbol_sets=4, rebase_cases=cases,
            original_mode_helper_words=150, original_default_words=34, connected_cases=cases_connected,
            full_memory_and_ordered_events_equal=True, mode_no_output_paths_preserve_original_private_bytes=True,
            cosine_is_bounded_callback_not_actual_trig_or_FCSR_claim=True,
            production_mode_helper_still_zero_stub_not_restored_here=True))

    def test_07_copied_owner_actual_padder_and_unchanged_neighbors(self):
        before = (self.out / 'before-source').read_text()
        objects = [compile_owner(self.root, self.out, body, name) for name, body in
            (('owner-before', before), ('owner-after', screen.install(before)))]
        for _, diagnostics in objects: self.assertEqual(diagnostics, [])
        old, old_functions, old_relocations = parse_object(objects[0][0])
        new, new_functions, new_relocations = parse_object(objects[1][0])
        self.assertEqual(old_functions.keys(), new_functions.keys())
        relative = lambda rels, f: {o - f['value']: r for o, r in rels.items() if f['value'] <= o < f['value'] + f['size']}
        for name, f in new_functions.items():
            if name == screen.FUNCTION:
                self.assertEqual(new[f['value']:f['value'] + f['size']], parse_object(self.out / 'selected.o')[0][:356])
                continue
            prev = old_functions[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_relocations, f)),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']], relative(old_relocations, prev)), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for i, (obj, _) in enumerate(objects):
            path = self.out / ('padded-%d.s' % i)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.out / 'before-guards' if i == 0 else self.guards, filename='generated_1E0560'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        old, of, _ = padded[0]
        new, nf, _ = padded[1]
        f = nf[screen.FUNCTION]
        self.assertEqual((f['value'], f['size']), (of[screen.FUNCTION]['value'], 356))
        self.assertEqual(new[:f['value']], old[:f['value']])
        self.assertEqual(new[f['value'] + 356:], old[f['value'] + 356:])
        self.assertEqual(nf['func_151B4B78']['value'] - f['value'], 356)
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_equal=True,
            zero_diagnostics=True, all_other_padded_owner_bytes_equal=True, target_size=356))

    def test_08_actual_padder_stale_word_and_relocation_controls(self):
        data = (self.out / 'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
        names_section = headers[header[13]]
        names = data[names_section[4]:names_section[4] + names_section[5]]
        text_sections = [s for s in headers if names[s[0]:].split(b'\0', 1)[0] == b'.text']
        self.assertEqual(len(text_sections), 1)
        text_offset = text_sections[0][4]
        raw_text = parse_object(self.out / 'selected.o')[0]
        for i in range(89):
            changed = bytearray(data)
            word = struct.unpack_from('>I', raw_text, i * 4)[0]
            struct.pack_into('>I', changed, text_offset + i * 4, word ^ 0x10000)
            obj = self.out / 'stale.o'
            obj.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'stale word patch.*\\+0x%X:' % (i * 4)):
                emit_padded_assembly(obj, self.out / 'slot.s', word_patches_path=self.out / 'isolated-guards.csv', filename='generated_1E0560')
        rows = [dict(row) for row in self.rows]
        rows[15]['expected_relocations'] = '-'
        path = self.out / 'stale-relocations.csv'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'stale relocations'):
            emit_padded_assembly(self.out / 'selected.o', self.out / 'slot.s', word_patches_path=path, filename='generated_1E0560')
        self.receipt('stale', dict(actual_padder_stale_word_rejections=89, relocated_JAL_control_effective=True))

    def test_09_entire_linked_ELF_protected_data_and_guard_history(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items(): self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('installation', dict(installed=False, production_baseline_unchanged=True))
            return
        self.assertEqual(source, screen.install((self.out / 'before-source').read_text()))
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith((self.out / 'before-guards').read_bytes()))
        self.assertEqual((self.root / self.paths['progress']).read_bytes(), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>89I', expected, elf_slot_offset(before, screen.ENTRY, 356), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 356)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, TABLE - start)[0], screen.ENTRY)
        self.receipt('installation', dict(installed=True, all_356_target_bytes_retail_exact=True,
            only_target_slot_and_symbol_extent_semantically_changed=True, decoded_ELF_metadata_equal=True,
            old_guard_prefix_and_conversion_rows_unchanged=True, protected_data=audit))

    def test_10_complete_original_renderer_adapter_helper_and_default(self):
        class ConnectedRenderer(renderer.RibbonOracle):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.adapter_calls = []

            def record_call(self, target):
                if target in (HELPER, DEFAULT, COS):
                    args = (self.f[12],) if target == COS else tuple(self.arguments(5 if target == HELPER else 14))
                    self.adapter_calls.append((target, *args))
                else:
                    super().record_call(target)

            def hook(self, target):
                if target == COS:
                    for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
                    self.f[:20] = [0xA5000000 + i for i in range(20)]
                    self.f[0] = bits(0.5)
                else:
                    super().hook(target)

        caller = list(struct.unpack_from('>475I', self.rom, renderer.screen.ROM))
        helper_words = list(struct.unpack_from('>150I', self.rom, 0x5C0E4))
        default_words = list(struct.unpack_from('>34I', self.rom, 0x1E1E3C))
        cases = 0
        for mode, pattern, phase, view in itertools.product(range(8), (0, 3), (0, 8), (0, 0xFFFF)):
            memory, vertex = renderer.fixture(pattern=pattern, view=view, selector=1)
            memory.update({OBJECT + i: (i * 17 + 0x35) & 255 for i in range(0x180)})
            initial.put(memory, ACTOR + 0x150, OBJECT)
            memory[OBJECT + 0xA4], memory[OBJECT + 0xA5], memory[OBJECT + 0xA6], memory[OBJECT + 0xA7] = mode, 37, 52, 71
            initial.put(memory, OBJECT + 0xA0, 83 if mode == 1 else 0x40802010)
            for i, value in enumerate(struct.unpack_from('>9I', self.rom, 0x23B9DC)):
                initial.put(memory, 0x80096F1C + i * 4, value)
            values = renderer.VALUES
            if mode & 1:
                colors, opacity = {1: ((37, 52, 71), 83), 3: ((0, 0, 0), 218),
                    5: ((128, 32, 16), 214), 7: ((128, 32, 16), 246)}[mode]
                values = (0x200005, 0x60600, *colors, 255, opacity, opacity, opacity, 255, 0x100000, 5, 0x2F)
            reference_model = renderer.RibbonReference(memory, view=view, vertex=vertex, values=values).run()
            outcomes = []
            for words in (self.retail, self.raw, self.fitted):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 356, 4), words))
                connected.update(zip(range(HELPER, HELPER + 600, 4), helper_words))
                connected.update(zip(range(DEFAULT, DEFAULT + 136, 4), default_words))
                model = ConnectedRenderer(caller, memory, view=view, phase=phase, vertex=vertex, connected=connected).run()
                self.assertEqual(model.calls, reference_model.calls)
                self.assertEqual(model.r[2], reference_model.result)
                self.assertEqual(renderer.external(model.memory), renderer.external(reference_model.memory))
                self.assertEqual(renderer.writes(model), reference_model.events)
                self.assertEqual(sum(c[0] == HELPER for c in model.adapter_calls), 1)
                self.assertEqual(sum(c[0] == DEFAULT for c in model.adapter_calls), int(not mode & 1))
                self.assertTrue(any(screen.ENTRY <= address < screen.ENTRY + 356 for address in model.visits))
                outcomes.append((model.memory, model.events, model.adapter_calls))
            self.assertEqual(outcomes[0], outcomes[1])
            self.assertEqual(outcomes[0], outcomes[2])
            cases += 1
        self.receipt('caller', dict(cases=cases, executions=cases * 3, original_renderer_words=475,
            original_adapter_words=89, original_mode_helper_words=150, original_default_words=34,
            custom_and_fallback_metadata_against_independent_strip_reference=True,
            signed_view_boundaries=True, bounded_graphics_and_cosine_callbacks_not_live_rendering=True))


if __name__ == '__main__':
    unittest.main()
