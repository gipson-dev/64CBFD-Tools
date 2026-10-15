"""View FOV callback protocol, cached/live data and guarded owner qualification."""
from collections import Counter
import csv
import hashlib
import itertools
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_fov_transfer_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_cosine_match as cosine
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_point_transform_match import put, read
from tools.check_game_data_layout import audit_layout
from tools.tests import view_fov_transfer_checkpoint as checkpoint
from tools.tests import view_projection_family_checkpoint as family_checkpoint

ENTRY, ATAN, COMMAND, BASE = source.ENTRY, 0x150484A0, 0x1510B128, 0x800BE628
WIDTHS, HEIGHTS, DEG_HALF, DEG_X, DEG_Y = 0x800BE638, 0x800BE650, 0x800968F4, 0x800968F8, 0x800968FC
VIEWS, ALTERNATE, THIRD = 0x24000, 0x28000, 0x2C000
RESULTS = (bits(0.25), bits(1.0), bits(-0.5), bits(2.0), bits(0.125), bits(-0.25), 0, 0x80000000, 0x7F800000, 0x7FC12345)
SERIALIZATION = (
    (('D_8009E530', 'D_8009E960', 'D_800A3300', 'D_80099000'), (3, 0, 1, 2),
     ((0x8009E530, 0, 16, 0, 6), (0x8009E960, 0, 16, 0, 6),
      (0x800A3300, 0, 16, 0, 65521), (0x80099000, 0, 16, 0, 65521))),
)


def fp(left, right, op):
    if op != 'div':
        return trig.operation(left, right, op)
    a, b = floating(left), floating(right)
    if math.isnan(a) or math.isnan(b):
        return bits(a + b)
    if b == 0.0:
        return 0x7FC00000 if a == 0 else bits(math.copysign(math.inf, a * math.copysign(1.0, b)))
    return bits(a / b)


def fixture(index=0, reference=1, phase=0):
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x180)}
    for base in (VIEWS, ALTERNATE, THIRD):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(-16, 0x900 + 16)})
        for slot in range(6):
            for offset, value in ((0xC, 160.0 + slot * 10), (0x10, 120.0 + slot * 5),
                                  (0x6C, 60.0 + slot * 5), (0x70, 45.0 + slot * 3)):
                put(memory, base + slot * 0x180 + offset, bits(value + (base - VIEWS) / 4096.0))
    memory.update({BASE + i: 0xA5 for i in range(-16, 80)})
    memory.update({DEG_HALF + i: 0xA5 for i in range(-16, 48)})
    put(memory, BASE, VIEWS)
    for i in range(6):
        put(memory, WIDTHS + i * 4, (320, 640, 0, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000)[i])
        put(memory, HEIGHTS + i * 4, (240, 480, 0xFFFFFFFF, 0, 0x80000000, 0x7FFFFFFF)[i])
    put(memory, DEG_HALF, 0x3C0EFA35)
    put(memory, DEG_X, 0x42E52EE0)
    put(memory, DEG_Y, 0x42E52EE0)
    return memory


def view(memory, index, offset):
    return (read(memory, BASE) + index * 0x180 + offset) & 0xFFFFFFFF


def effects(memory, index, reference, ordinal, mode):
    if mode == 1 and ordinal == 1:
        put(memory, BASE, ALTERNATE)
        put(memory, DEG_HALF, bits(2.0))
        put(memory, ALTERNATE + index * 0x180 + 0x70, bits(179.0))
    if mode == 2 and ordinal == 4:
        put(memory, WIDTHS + reference * 4, 777)
        put(memory, HEIGHTS + reference * 4, 555)
        put(memory, BASE, ALTERNATE)
    if mode == 3 and ordinal == 5:
        put(memory, BASE, THIRD)
        put(memory, DEG_X, bits(8.0))
        put(memory, WIDTHS + reference * 4, 999)
        put(memory, HEIGHTS + reference * 4, 999)
    if mode == 4 and ordinal == 6:
        put(memory, BASE, ALTERNATE)
        put(memory, DEG_Y, bits(-4.0))
        put(memory, ALTERNATE + reference * 0x180 + 0x70, bits(33.0))
    if mode == 5 and ordinal == 7:
        put(memory, BASE, THIRD)
        put(memory, THIRD + index * 0x180 + 0x74, 0x12345678)


def answer(seed, ordinal):
    return RESULTS[(seed + ordinal * 3) % len(RESULTS)]


def reference_model(memory, index, reference, seed=0, mode=0, real_trig=False):
    result, calls = dict(memory), []
    half_x = fp(read(result, view(result, index, 0x6C)), read(result, DEG_HALF), 'mul')
    half_y = fp(read(result, view(result, index, 0x70)), read(result, DEG_HALF), 'mul')
    def call(target, arguments):
        ordinal = len(calls) + 1
        calls.append((target, arguments))
        value = (trig.reference(arguments[0]) if target == trig.ENTRY else cosine.reference(arguments[0])) if real_trig and target in (trig.ENTRY, cosine.ENTRY) else answer(seed, ordinal)
        effects(result, index, reference, ordinal, mode)
        return value
    sine_x = call(trig.ENTRY, (half_x,))
    cosine_x = call(cosine.ENTRY, (half_x,))
    tangent_x = fp(sine_x, cosine_x, 'div')
    sine_y = call(trig.ENTRY, (half_y,))
    cosine_y = call(cosine.ENTRY, (half_y,))
    tangent_y = fp(sine_y, cosine_y, 'div')
    extent_x = fp(bits(float(signed(read(result, WIDTHS + reference * 4)))), fp(tangent_x, tangent_x, 'add'), 'div')
    extent_y = fp(bits(float(signed(read(result, HEIGHTS + reference * 4)))), fp(tangent_y, tangent_y, 'add'), 'div')
    angle_x = call(ATAN, (read(result, view(result, index, 0xC)), extent_x))
    offset_x = fp(fp(angle_x, read(result, DEG_X), 'mul'), read(result, view(result, reference, 0x6C)), 'sub')
    angle_y = call(ATAN, (read(result, view(result, index, 0x10)), extent_y))
    offset_y = fp(fp(angle_y, read(result, DEG_Y), 'mul'), read(result, view(result, reference, 0x70)), 'sub')
    call(COMMAND, (index, offset_x, offset_y, 0x3F800000, 0))
    return result, calls


class TransferOracle(cosine.CosineOracle):
    def __init__(self, words, memory, index=0, reference=1, seed=0, mode=0, phase=0, fault=None, connected=None):
        super().__init__(words, memory, phase=phase, entry=ENTRY, arguments=(index, reference), connected=connected)
        self.index, self.reference, self.seed, self.mode = index, reference, seed, mode
        self.root_fault, self.root_accesses = fault, 0

    def access(self):
        if self.own_instruction and ENTRY <= self.current_pc < ENTRY + 396:
            if self.root_accesses == self.root_fault:
                raise faults.AccessBoundary
            self.root_accesses += 1

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 3:
            self.f[word >> 6 & 31] = fp(self.f[word >> 11 & 31], self.f[word >> 16 & 31], 'div')
        else:
            super().execute(word)

    def record_call(self, target):
        if target in (trig.ENTRY, cosine.ENTRY):
            arguments = (self.f[12],)
        elif target == ATAN:
            arguments = (self.f[12], self.f[14])
        else:
            assert target == COMMAND
            arguments = self.arguments(5)
        self.calls.append((target, arguments))
        self.events.append(('CALL', target, arguments))

    def hook(self, target):
        ordinal = len(self.calls)
        effects(self.memory, self.index, self.reference, ordinal, self.mode)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2], self.f[0] = 0x11223344 + ordinal, answer(self.seed, ordinal)


class ViewFovTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>99I', cls.rom, source.ROM))
        cls.obj, cls.warnings = build.compile_owner(cls.root, cls.out, source.recover((cls.out / 'before-owner').read_text()), 'qualified-owner')
        cls.guards = cls.out / 'qualified-guards.csv'
        cls.guards.write_bytes((cls.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        return obj

    def words(self):
        if not hasattr(type(self), 'cached_words'):
            data, functions = build.link_owner(self.root, self.out, self.out / 'primary-padded.o', source.OWNER)
            type(self).cached_words = list(struct.unpack_from('>99I', data, functions[source.FUNCTION]['value']))
        return type(self).cached_words

    def test_01_owner_neighbors_closed_schedule_and_both_padders(self):
        old, warnings = build.compile_owner(self.root, self.out, (self.out / 'before-owner').read_text(), 'before-owner-object')
        a, af, ar = parse_object(old)
        b, bf, br = parse_object(self.obj)
        self.assertEqual((warnings, self.warnings), ('', ''))
        self.assertEqual(set(af), set(bf))
        for name in set(af) - {source.FUNCTION}:
            x, y = af[name], bf[name]
            self.assertEqual(x['size'], y['size'], name)
            self.assertEqual(a[x['value']:x['value'] + x['size']], b[y['value']:y['value'] + y['size']], name)
            rel = lambda table, info: {offset - info['value']: value for offset, value in table.items() if info['value'] <= offset < info['value'] + info['size']}
            self.assertEqual(rel(ar, x), rel(br, y), name)
        self.assertEqual(normalized_pools(old), normalized_pools(self.obj))
        info = bf[source.FUNCTION]
        self.assertEqual(info['size'], 396)
        words = list(struct.unpack_from('>99I', b, info['value']))
        self.assertEqual(words[0], 0x27BDFFB0)
        before_atoms, after_atoms = [], []
        for offset, expected, replacement, before, after in source.GUARDS:
            self.assertEqual(words[offset // 4], expected)
            actual = br.get(info['value'] + offset, [])
            self.assertEqual(actual, pad_c_object.parse_relocation_spec(before) or [])
            before_atoms.append((expected, tuple(actual)))
            after_atoms.append((replacement, tuple(pad_c_object.parse_relocation_spec(after) or [])))
        self.assertEqual(Counter(before_atoms), Counter(after_atoms))
        primary = pad_c_object.emit_padded_assembly(self.obj, self.root / 'conker/retail_layout.us.txt', source.OWNER, word_patches_path=self.guards)
        self.assemble(primary, 'primary-padded')
        emitted, unresolved = emit_function(b, info, br, source.FUNCTION, nm_anchors(self.root / source.PATHS['elf']))
        self.assertFalse(unresolved)
        compact = self.assemble(emitted, 'compact')
        selected = self.out / 'selected-guards.csv'
        selected.write_text(self.guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)
        generated = self.assemble(emit_padded_assembly(compact, self.root / source.PATHS['original'], filename=source.OWNER, word_patches_path=selected), 'generated-padded')
        data, f = build.link_owner(self.root, self.out, generated, source.OWNER)
        self.assertEqual(data[f[source.FUNCTION]['value']:f[source.FUNCTION]['value'] + 396], self.rom[source.ROM:source.ROM + 396])
        self.assertEqual(self.words(), self.retail)
        self.receipt('owner', neighbors=len(af) - 1, words=99, frame=80, guards=13, closed_word_and_relocation_multiset=True, both_padders=True, pools_and_retained_sizes_words_relocations_fixed=True)

    def test_02_independent_original_and_rebased_links(self):
        original = self.assemble((self.root / source.PATHS['original']).read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',396\n', 'original')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        for delta in (0, 0x9000):
            outputs = []
            for label, obj in (('c', self.out / 'generated-padded.o'), ('retail', original)):
                script = self.out / ('rebase-' + label + '-' + str(delta) + '.ld')
                script.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n' % (ENTRY + delta))
                elf = script.with_suffix('.elf')
                _, _, relocations = parse_object(obj)
                used = {symbol for entries in relocations.values() for _, symbol in entries}
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, anchors[name] + delta) for name in sorted(used)], '-o', str(elf), str(obj)], check=True, capture_output=True)
                outputs.append(sections(elf)['.text'][1])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebase', comparisons=4, independent_original_and_code_data_helper_rebases=True)

    def test_03_mips_cached_live_inputs_aliases_and_full_state(self):
        cases, coverage = 0, set()
        for index, reference, seed, mode, phase in itertools.product((0, 1, 3), range(6), range(10), range(6), (0, 8)):
            memory = fixture(index, reference, phase)
            expected, calls = reference_model(memory, index, reference, seed, mode)
            models = [TransferOracle(words, memory, index, reference, seed, mode, phase).run() for words in (self.retail, self.words())]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual({a: v for a, v in model.memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180},
                                 {a: v for a, v in expected.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180})
                coverage.update(model.visits)
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            cases += 1
        self.assertEqual(coverage, set(range(ENTRY, ENTRY + 396, 4)))
        self.receipt('mips', paired_cases=cases, all_99_words=True, helper_calls=7, cached_initial_half_angles_live_later_bases_dimensions_and_coefficients=True,
                     equal_view_aliases=True, full_available_state=True, no_FCSR_or_arbitrary_helper_semantics_claim=True)

    def test_04_every_fired_root_memory_prefix(self):
        cases = 0
        for mode, phase in itertools.product(range(6), (0, 8)):
            memory = fixture(1, 1, phase)
            full = TransferOracle(self.retail, memory, 1, 1, 2, mode, phase).run()
            for cut in range(full.root_accesses):
                models = [TransferOracle(words, memory, 1, 1, 2, mode, phase, cut) for words in (self.retail, self.words())]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cases += 1
        self.receipt('faults', fired_root_prefixes=cases, actual_PC_and_delay_identity=True, helpers_atomic_bounded_no_native_C_fault_claim=True)

    def test_05_corrupt_expected_word_and_relocation_rejected(self):
        for field, value in (('expected', '0xAFBF001D'), ('expected_relocations', 'R_MIPS_LO16:D_800968F4')):
            rows = list(csv.DictReader(io.StringIO(self.guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)))
            self.assertNotEqual(rows[0][field], value)
            rows[0][field] = value
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
            path = self.out / 'negative-guards.csv'
            path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.out / 'compact.o', self.root / source.PATHS['original'], filename=source.OWNER, word_patches_path=path)

    def native(self, body, label, status=0, preamble=source.PREAMBLE):
        finite = RESULTS[:6]
        records = []
        with patch(__name__ + '.RESULTS', finite):
            for index, ref, seed, mode in itertools.product((0, 1, 3), range(6), range(6), range(6)):
                memory = fixture(index, ref)
                expected, calls = reference_model(memory, index, ref, seed, mode)
                native_views = []
                for region, base in enumerate((VIEWS, ALTERNATE, THIRD)):
                    for offset in range(0, 0x900, 4):
                        numeric = offset % 0x180 in (0xC, 0x10, 0x6C, 0x70) or (
                            mode == 5 and region == 2 and offset == index * 0x180 + 0x74)
                        native_views.append(read(expected, base + offset) if numeric else
                            int.from_bytes(bytes(expected[base + offset + i] for i in range(4)), 'little'))
                records.append(dict(index=index, ref=ref, seed=seed, mode=mode,
                    calls=[[target, *args, *([0] * (5 - len(args)))] for target, args in calls],
                    views=native_views,
                    widths=[read(expected, WIDTHS + i * 4) for i in range(6)],
                    heights=[read(expected, HEIGHTS + i * 4) for i in range(6)],
                    globals=[(read(expected, BASE) - VIEWS) // 0x4000, read(expected, DEG_HALF), read(expected, DEG_X), read(expected, DEG_Y)]))
        literal = lambda values: '{' + ','.join('0x%Xu' % value for value in values) + '}'
        rows = []
        for record in records:
            rows.append('{%d,%d,%d,%d,{%s},%s,%s,%s,%s}' % (
                record['index'], record['ref'], record['seed'], record['mode'],
                ','.join(literal(call) for call in record['calls']), literal(record['views']),
                literal(record['widths']), literal(record['heights']), literal(record['globals'])))
        program = '''typedef unsigned char u8; typedef unsigned int u32; typedef int s32; typedef float f32;
''' + preamble + '''
ViewProjection476D0 storage[3][6];
u8 *D_800BE628;
s32 D_800BE638[6], D_800BE650[6];
f32 D_800968F4,D_800968F8,D_800968FC;
typedef struct {s32 index,ref,seed,mode;u32 calls[7][6],views[1728],widths[6],heights[6],globals[4];} Case;
static Case cases[]={''' + ',\n'.join(rows) + '''};
static const u32 answers[]={''' + ','.join('0x%Xu' % value for value in finite) + '''};
static Case *current; static u32 calls[7][6]; static int count,error;
static u32 word(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
static f32 number(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static void putword(void *p,u32 value){u8 *b=p;int i;for(i=0;i<4;i++){b[i]=value&255;value>>=8;}}
static u32 getword(const void *p){const u8 *b=p;return (u32)b[0]|(u32)b[1]<<8|(u32)b[2]<<16|(u32)b[3]<<24;}
static void effect(int ordinal){int index=current->index,ref=current->ref,mode=current->mode;
 if(mode==1&&ordinal==1){D_800BE628=(u8 *)storage[1];D_800968F4=2.0f;storage[1][index].baseFovY=179.0f;}
 if(mode==2&&ordinal==4){D_800BE638[ref]=777;D_800BE650[ref]=555;D_800BE628=(u8 *)storage[1];}
 if(mode==3&&ordinal==5){D_800BE628=(u8 *)storage[2];D_800968F8=8.0f;D_800BE638[ref]=999;D_800BE650[ref]=999;}
 if(mode==4&&ordinal==6){D_800BE628=(u8 *)storage[1];D_800968FC=-4.0f;storage[1][ref].baseFovY=33.0f;}
 if(mode==5&&ordinal==7){D_800BE628=(u8 *)storage[2];putword((u8 *)&storage[2][index]+0x74,0x12345678);}
}
static f32 submit(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e){int ordinal=++count;
 if(ordinal>7){error=1;return 0;}
 calls[ordinal-1][0]=target;calls[ordinal-1][1]=a;calls[ordinal-1][2]=b;calls[ordinal-1][3]=c;calls[ordinal-1][4]=d;calls[ordinal-1][5]=e;
 effect(ordinal);return number(answers[(current->seed+ordinal*3)%6]);}
f32 sinf(f32 x){return submit(0x15047D60,word(x),0,0,0,0);}
f32 cosf(f32 x){return submit(0x15047C00,word(x),0,0,0,0);}
f32 func_150484A0(f32 x,f32 y){return submit(0x150484A0,word(x),word(y),0,0,0);}
s32 func_1510B128(s32 index,f32 x,f32 y,f32 scale,f32 fallback){submit(0x1510B128,index,word(x),word(y),word(scale),word(fallback));return 0x1122334B;}
''' + body + '''
static int run(void){int n,b,i,j,k;u8 *bytes;
 if(sizeof(ViewProjection476D0)!=0x180||__builtin_offsetof(ViewProjection476D0,extentX)!=0xC||__builtin_offsetof(ViewProjection476D0,baseFovX)!=0x6C)return 90;
 for(n=0;n<(int)(sizeof(cases)/sizeof(cases[0]));n++){
  current=&cases[n];count=error=0;
  for(b=0;b<3;b++){bytes=(u8 *)storage[b];for(i=0;i<0x900;i++)bytes[i]=(i*13+0xA5)&255;
   for(i=0;i<6;i++){storage[b][i].extentX=160.0f+i*10+b*4;storage[b][i].extentY=120.0f+i*5+b*4;storage[b][i].baseFovX=60.0f+i*5+b*4;storage[b][i].baseFovY=45.0f+i*3+b*4;}}
  D_800BE628=(u8 *)storage[0];D_800968F4=number(0x3C0EFA35);D_800968F8=D_800968FC=number(0x42E52EE0);
  {static u32 widths[]={320,640,0,0xFFFFFFFF,0x7FFFFFFF,0x80000000};static u32 heights[]={240,480,0xFFFFFFFF,0,0x80000000,0x7FFFFFFF};for(i=0;i<6;i++){D_800BE638[i]=(s32)widths[i];D_800BE650[i]=(s32)heights[i];}}
  func_1501B0A0(current->index,current->ref);
  if(error||count!=7)return 1;
  for(i=0;i<7;i++)for(j=0;j<6;j++)if(calls[i][j]!=current->calls[i][j])return 1;
  for(b=0;b<3;b++)for(i=0;i<0x900;i+=4){k=b*576+i/4;if(getword((u8 *)storage[b]+i)!=current->views[k])return 2;}
  for(i=0;i<6;i++)if((u32)D_800BE638[i]!=current->widths[i]||(u32)D_800BE650[i]!=current->heights[i])return 2;
  if(D_800BE628!=(u8 *)storage[current->globals[0]]||word(D_800968F4)!=current->globals[1]||word(D_800968F8)!=current->globals[2]||word(D_800968FC)!=current->globals[3])return 2;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        path = self.out / ('native-' + label + '.c')
        path.write_text(program)
        for profile in ('-O2', '-O0'):
            binary = path.with_suffix('.' + profile[1:])
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-fno-strict-aliasing', '-fwrapv', '-fno-builtin', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label + profile)
        return len(records)

    def test_06_native32_live_state_and_effective_controls(self):
        cases = self.native(source.BODY, 'selected')
        controls = {
            'reload-half': source.BODY.replace('    tangentY =', '    halfY = VIEW_PROJECTIONS_476D0[index].baseFovY * D_800968F4;\n    tangentY ='),
            'early-dimensions': dict(source.variants())['early-extents'],
            'unsigned-width': source.BODY.replace('((s32 *)&D_800BE638)', '((u32 *)&D_800BE638)'),
            'wrong-scale': source.BODY.replace('offsetY, 1.0f, 0.0f', 'offsetY, 0.0f, 0.0f'),
        }
        for label, body in controls.items():
            self.native(body, label, 1)
        self.receipt('native', cases_per_profile=cases, profiles=['O2', 'O0'], controls=list(controls),
                     all_7_helper_argument_packets_and_storage_globals_checked=True,
                     finite_nonzero_trig_returns=True, no_arithmetic_NaN_payload_FCSR_index_wrap_or_native_fault_claim=True)

    def test_07_connected_recovered_trig_with_bounded_angle_and_command(self):
        connected = {}
        for entry, offset, words in ((trig.ENTRY, trig.ROM, 104), (cosine.ENTRY, cosine.ROM, 88)):
            name = 'sinf' if entry == trig.ENTRY else 'cosf'
            obj, warnings = build.compile_owner(self.root, self.out, (self.root / source.PATHS[name]).read_text(), 'connected-' + name)
            data, _ = build.link_owner(self.root, self.out, obj, name)
            self.assertEqual(warnings, '')
            self.assertEqual(data, self.rom[offset:offset + words * 4])
            connected.update(zip(range(entry, entry + words * 4, 4), struct.unpack('>%dI' % words, data)))
        cases = 0
        for index, ref, phase in itertools.product((0, 1, 3), range(6), (0, 8)):
            memory = fixture(index, ref, phase)
            for address, value in {**trig.GLOBALS, **trig.COS_GLOBALS}.items():
                put(memory, address, value)
            expected, calls = reference_model(memory, index, ref, 0, 0, real_trig=True)
            models = [TransferOracle(words, memory, index, ref, 0, 0, phase, connected=connected).run() for words in (self.retail, self.words())]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual({a: v for a, v in model.memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180},
                                 {a: v for a, v in expected.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180})
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            cases += 1
        self.receipt('connected', paired_cases=cases, both_trig_bodies_compiled_and_retail_exact=True,
                     angle_helper_and_final_command_bounded_models=True, no_actual_command_callee_or_gameplay_acceptance=True)

    def test_08_installed_source_guards_and_closed_image(self):
        source.freeze(self.root, self.out)
        old = lambda data, key: family_checkpoint.previous_input(data, source.PATHS[key], self.root)
        self.assertEqual(old((self.root / source.PATHS['owner']).read_text().encode(), 'owner').decode(), source.recover((self.out / 'before-owner').read_text()))
        self.assertEqual(old((self.root / source.PATHS['owner']).read_bytes(), 'owner'), source.recover((self.out / 'before-owner').read_text()).encode())
        self.assertEqual(old((self.root / source.PATHS['guards']).read_bytes(), 'guards'), (self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        for key, path in source.PATHS.items():
            if key not in ('owner', 'guards', 'elf'):
                self.assertEqual(old((self.root / path).read_bytes(), key), (self.out / ('before-' + key)).read_bytes(), key)
        before = (self.out / 'before-elf').read_bytes()
        current = old((self.root / source.PATHS['elf']).read_bytes(), 'elf')
        expected = bytearray(before)
        at = trig.image.elf_slot_offset(before, ENTRY, 396)
        expected[at:at + 396] = self.rom[source.ROM:source.ROM + 396]
        with patch.object(trig.image.screen, 'ENTRY', ENTRY):
            size = trig.image.elf_symbol_size_offset(before, source.FUNCTION)
        self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
        struct.pack_into('>I', expected, size, 396)
        with patch.object(machine, 'SERIALIZATION', SERIALIZATION):
            machine.apply_burst_symbol_serialization(expected)
        self.assertEqual(current, bytes(expected), 'Only view-transfer slot, public extent and one closed symbol/string group may change')
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256(current).hexdigest(),
                     owner_sha256=hashlib.sha256((self.root / source.PATHS['owner']).read_bytes()).hexdigest(),
                     guards_sha256=hashlib.sha256((self.root / source.PATHS['guards']).read_bytes()).hexdigest(),
                     changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + 396], current[at:at + 396])),
                     extent_before=12, extent_after=396, exact_symbol_groups=1,
                     non_target_symbol_definition_changes=0, every_other_ELF_byte_fixed=True, protected_data=data)

    def test_09_effective_installed_and_frozen_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_08_installed_source_guards_and_closed_image()
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_08_installed_source_guards_and_closed_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable view-transfer input'):
                source.freeze(self.root, self.out)

    def test_10_pinned_inverse_unknown_input_and_capture_controls(self):
        self.test_08_installed_source_guards_and_closed_image()
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            data = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data, self.root / relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data + b'\n', relative, self.root), data + b'\n')
        rb = Path.read_bytes
        path = self.out / 'after-owner'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'view transfer fixture'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
