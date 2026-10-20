"""Float/int boundaries, post-call actor reads, canonical vector and retail math chain."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_heading_projected_speed as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
ACTOR, OTHER = 0x28000, 0x29000
NAMES = {'func_150490A8': source.HEADING, 'func_15048A40': source.SCALE,
         'func_15048864': source.ACOS, 'func_150489B0': source.SINE}
BANKS = ((0x80098E00, 0x220), (0x8009A220, 260))
POSES = ((bits(1.75), bits(-2.75)), (0x80000000, bits(0.5)),
         (0x4EFFFFFF, 0xCF000000), (bits(16777216.0), bits(-16777216.0)))
ORIGINS = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x12345678)
SCALES = (0, 0x80000000, bits(1), bits(-1), bits(0.5), bits(-0.5), 0x3EAAAAAB, bits(-0.25))
SPEEDS = (0, 0x80000000, bits(5.75), bits(-17.25), bits(1024.125))


def f32(value):
    return floating(bits(value))


def trunc(value):
    assert math.isfinite(value) and -2147483648.0 <= value < 2147483648.0, ('unqualified conversion', value)
    return math.trunc(value)


@dataclass(frozen=True)
class Case:
    x: int = POSES[0][0]
    z: int = POSES[0][1]
    origin_x: int = 0
    origin_z: int = 0
    facing: int = 0x1234
    speed: int = SPEEDS[2]
    heading: int = 64
    scale: int = SCALES[4]
    mutations: int = 0
    home: int = 0
    unused: int = 0xF00DBAAD
    seed: int = 0xA5


def corpus():
    for i in range(256):
        yield Case(*POSES[i % 4], ORIGINS[i % 6], ORIGINS[(i + 2) % 6],
                   i << 8 | (i * 13 & 255), SPEEDS[i % 5], 0, SCALES[i % 8],
                   unused=i * 0x1234567 & 0xFFFFFFFF)
    for i, (pose, heading, mutations) in enumerate(itertools.product(range(4),
            (0, 63, 64, 127, 128, 191, 192, 255), range(4))):
        yield Case(*POSES[pose], ORIGINS[i % 6], ORIGINS[(i + 3) % 6],
                   (0, 0x00FF, 0xFF00, 0xFFFF)[i % 4], SPEEDS[i % 5], heading,
                   SCALES[i % 8], mutations)
    for home, seed in itertools.product(range(4), (0xA5, 0x5A)):
        yield Case(mutations=3, home=home, seed=seed)


def fixture(case, banks, delta=0):
    memory = {STACK + i: (i * 17 + case.seed) & 255 for i in range(-0x500, 0x100)}
    for base in (ACTOR + delta, OTHER + delta):
        memory.update({base + i: 0xA5 for i in range(256)})
    for base, x, z, speed, facing in (
            (ACTOR + delta, case.x, case.z, case.speed, case.facing),
            (OTHER + delta, bits(-50.25), bits(1000.75), bits(27.25), 0xE1C3)):
        for offset, value, size in ((0x14, x, 4), (0x1C, z, 4), (0x3C, speed, 4), (0x76, facing, 2)):
            put(memory, base + offset, value, size)
    for address, data in banks.items():
        memory.update({address + i: byte for i, byte in enumerate(data)})
    return memory


def public_event(event, delta=0):
    if event[0] == 'CALL':
        return event[1] in ('HEADING', 'SCALE')
    return any(base <= event[1] < base + 256 for base in (ACTOR + delta, OTHER + delta))


def public_memory(memory, delta=0):
    return {a: value for a, value in memory.items()
            if any(base <= a < base + 256 for base in (ACTOR + delta, OTHER + delta))}


def offset_bits(case):
    dx = signed((trunc(floating(case.x)) - signed(case.origin_x)) & 0xFFFFFFFF)
    dz = signed((trunc(floating(case.z)) - signed(case.origin_z)) & 0xFFFFFFFF)
    return bits(float(dx)), bits(float(dz))


def original_heading(memory, point):
    x, z = map(floating, point)
    length = f32(math.sqrt(f32(f32(x * x) + f32(z * z))))
    if length == 0.0:
        return 0
    ratio = f32(x / length)
    index = trunc(f32(abs(ratio) * floating(read(memory, 0x80099008))))
    assert 0 <= index <= 256
    value = read(memory, 0x80098E00 + index * 2, 2) >> 10
    angle = 255 - value if ratio < 0.0 else value
    return (128 - angle if angle < 64 else 384 - angle) if z > 0.0 else angle


def original_scale(memory, angle):
    phase = (angle - 64) & 255
    index, negative = ((phase, False) if phase <= 64 else (128 - phase, True)
                       if phase <= 128 else (phase - 128, True) if phase <= 192 else (256 - phase, False))
    return read(memory, 0x8009A220 + index * 4) ^ (0x80000000 if negative else 0)


def changes(case, stage, delta=0):
    if stage == 'HEADING' and case.mutations & 1:
        return ((ACTOR + delta + 0x14, bits(10), 4), (ACTOR + delta + 0x1C, bits(20), 4),
                (ACTOR + delta + 0x76, 0x2A6F, 2), (ACTOR + delta + 0x3C, bits(-13.75), 4))
    if stage == 'SCALE' and case.mutations & 2:
        return (((OTHER if case.home & 1 else ACTOR) + delta + 0x3C, bits(17.75), 4),)
    return ()


def reference(initial, case, delta=0, connected=False):
    memory, events = initial.copy(), []
    point = offset_bits(case)
    events += [('R', ACTOR + delta + 0x14, 4, case.x), ('R', ACTOR + delta + 0x1C, 4, case.z),
               ('CALL', 'HEADING', point)]
    heading = original_heading(memory, point) if connected else case.heading
    assert 0 <= heading <= 255
    for address, value, size in changes(case, 'HEADING', delta):
        put(memory, address, value, size);events.append(('W', address, size, value))
    actor = (OTHER if case.home & 1 else ACTOR) + delta
    facing = read(memory, actor + 0x76, 2)
    events.append(('R', actor + 0x76, 2, facing))
    angle = (64 - (facing >> 8) - heading) & 255
    events.append(('CALL', 'SCALE', (angle,)))
    scale = original_scale(memory, angle) if connected else case.scale
    for address, value, size in changes(case, 'SCALE', delta):
        put(memory, address, value, size);events.append(('W', address, size, value))
    if case.home & 2:
        actor = (ACTOR if case.home & 1 else OTHER) + delta
    speed = read(memory, actor + 0x3C)
    events.append(('R', actor + 0x3C, 4, speed))
    result = trunc(f32(floating(speed) * floating(scale))) & 0xFFFFFFFF
    return memory, events, result, point, angle


class ProjectionOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0, delta=0, symbols=None,
                 entry=source.ENTRY, connected=None):
        self.case, self.delta = case, delta
        self.by_address = {v: k for k, v in (symbols or NAMES).items()}
        self.entered_sp = STACK + phase
        self.middle, self.fired = None, []
        super().__init__(words, memory, phase=phase, entry=entry,
                         arguments=(case.origin_x, case.origin_z, case.unused, ACTOR + delta), connected=connected)

    def execute(self, word):
        op, rs, rd, fd, fn = word >> 26, word >> 21 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        # Extend the existing runner only for scalar operations already used by sibling math oracles.
        if op == 17 and rs == 16 and fn in (4, 5, 7, 13):
            if fn == 4:
                value = floating(self.f[rd]);assert value >= 0 and math.isfinite(value)
                self.f[fd] = bits(math.sqrt(value))
            elif fn == 5:self.f[fd] = self.f[rd] & 0x7FFFFFFF
            elif fn == 7:self.f[fd] = self.f[rd] ^ 0x80000000
            else:self.f[fd] = trunc(floating(self.f[rd])) & 0xFFFFFFFF
        else:super().execute(word)

    def record_call(self, target):
        name = self.by_address[target]
        if name == 'func_150490A8':
            pointer = self.r[4]
            self.middle = bytes(self.memory[pointer + i] for i in range(4, 8))
            args = (read(self.memory, pointer), read(self.memory, pointer + 8))
            label = 'HEADING'
        elif name == 'func_15048A40':label, args = 'SCALE', self.arguments(1)
        elif name == 'func_15048864':label, args = 'ACOS', (self.f[12],)
        else:label, args = 'SINE', self.arguments(1)
        self.calls.append((label, args));self.events.append(('CALL', label, args))
        for address, value, size in changes(self.case, label, self.delta):
            self.put(address, value, size)
        if label == 'HEADING' and self.case.home & 1:
            self.put(self.entered_sp + 12, OTHER + self.delta, 4);self.fired.append('actor-home-after-heading')
        if label == 'SCALE' and self.case.home & 2:
            self.put(self.entered_sp + 12, (ACTOR if self.case.home & 1 else OTHER) + self.delta, 4)
            self.fired.append('actor-home-after-scale')
        if label == 'HEADING' and self.case.home:
            self.put(self.entered_sp, 0x13579BDF, 4);self.put(self.entered_sp + 8, 0x2468ACE0, 4)
            self.fired.append('finished-origin-and-unused-homes')

    def hook(self, target):
        label = self.by_address[target]
        assert label in ('func_150490A8', 'func_15048A40')
        for i in range(4):self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        if label == 'func_150490A8':self.r[2] = self.case.heading
        else:self.f[0] = self.case.scale


def native_harness(body, cases, banks):
    rows = []
    for case in cases:
        _, _, result, point, angle = reference(fixture(case, banks), case)
        rows.append('{'+','.join('0x%Xu'%v for v in (
            case.x, case.z, case.origin_x, case.origin_z, case.facing, case.speed, case.heading,
            case.scale, case.mutations, case.unused, *point, angle, result))+'}')
    declarations = source.DECLARATIONS.replace('#include "structs.h"',
        'typedef struct {f32 unk0,unk4,unk8;} struct17;')
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned short u16;
typedef unsigned char u8;typedef float f32;
''' + declarations + '''
typedef char vector_size_is_12[sizeof(struct17)==12 ? 1 : -1];
''' + body + '''
typedef struct {u8 p0[20];f32 x;u8 p1[4];f32 z;u8 p2[28];f32 speed;u8 p3[54];u16 facing;u8 tail[136];} Actor;
typedef char actor_size_is_256[sizeof(Actor)==256 ? 1 : -1];
typedef char facing_offset_is_76[__builtin_offsetof(Actor,facing)==0x76 ? 1 : -1];
typedef struct {u32 x,z,originX,originZ,facing,speed,heading,scale,mutations,unused,dx,dz,angle,result;} Case;
static const Case cases[]={
''' + ',\n'.join(rows) + '''
};
static const Case *item;static Actor actor;static int stage,error;
static u32 word(f32 f) {union {f32 f;u32 u;} v;v.f=f;return v.u;}
static f32 real(u32 u) {union {f32 f;u32 u;} v;v.u=u;return v.f;}
s32 func_150490A8(struct17 *point) {
    if(stage++!=0 || word(point->unk0)!=item->dx || word(point->unk8)!=item->dz)error=1;
    if(item->mutations&1) {actor.x=10.0f;actor.z=20.0f;actor.facing=0x2A6F;actor.speed=-13.75f;}
    return (s32)item->heading;
}
f32 func_15048A40(u8 angle) {
    if(stage++!=1 || angle!=item->angle)error=1;
    if(item->mutations&2)actor.speed=17.75f;
    return real(item->scale);
}
static int test_all(void) {
    u32 n,i;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++) {
        s32 result;item=&cases[n];stage=error=0;
        for(i=0;i<256;i++)((u8 *)&actor)[i]=0xA5;
        actor.x=real(item->x);actor.z=real(item->z);actor.speed=real(item->speed);actor.facing=(u16)item->facing;
        result=func_15116888((s32)item->originX,(s32)item->originZ,(void *)item->unused,&actor);
        if(error || stage!=2 || (u32)result!=item->result)return 23;
        if(word(actor.x)!=((item->mutations&1)?word(10.0f):item->x) ||
           word(actor.z)!=((item->mutations&1)?word(20.0f):item->z) ||
           actor.facing!=((item->mutations&1)?0x2A6F:item->facing))return 24;
        if(word(actor.speed)!=((item->mutations&2)?word(17.75f):(item->mutations&1)?word(-13.75f):item->speed))return 24;
        for(i=0;i<256;i++) {
            if((i>=0x14&&i<0x18)||(i>=0x1C&&i<0x20)||(i>=0x3C&&i<0x40)||(i>=0x76&&i<0x78))continue;
            if(((u8 *)&actor)[i]!=0xA5)return 25;
        }
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();
}
'''


class HeadingProjectedSpeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.installed = source.digest((ROOT / source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT, cls.output)
        else:
            source.qualify(ROOT, cls.output);source.make_shadow(ROOT, cls.output);source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output)
        cls.obj, diagnostic = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n' + source.DECLARATIONS + source.SELECTED, 'fresh-selected')
        if diagnostic:raise ValueError(diagnostic)
        cls.original = source.original(ROOT, cls.output)
        image, funcs = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>39I', image, funcs[source.FUNCTION]['value']))
        rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>39I', rom, source.ROM))
        cls.helpers = {entry:list(struct.unpack_from('>%dI'%count,rom,offset)) for entry,offset,count in source.HELPERS}
        before = cls.values['conker/build/conker.us.elf']
        cls.banks = {address:before[source.elf_slot_offset(before,address,size):source.elf_slot_offset(before,address,size)+size]
                     for address,size in BANKS}
        cls.cases = list(corpus());cls.native_cases = [c for c in cls.cases if not c.home]
        cls.receipt = dict(cases=len(cls.cases),native_cases=len(cls.native_cases),installed=cls.installed,
                           matching_credit=int(cls.installed),guards=0,compiler_only=True)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('heading projection qualification:',cls.receipt)

    def run_model(self, words, case, phase=0, connected=False, delta=0, symbols=None, entry=source.ENTRY):
        code={}
        if connected:
            self.assertIsNone(symbols)
            for address, data in self.helpers.items():code.update(zip(range(address,address+len(data)*4,4),data))
        return ProjectionOracle(words,fixture(case,self.banks,delta),case,phase,delta,symbols,entry,code).run()

    def native(self, body, label, optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases,self.banks))
        binary=self.output/(label+optimization)
        args=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
              '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign',
              '-ffp-contract=off','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
              '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(binary)],capture_output=True,timeout=30)

    def test_complete_C_original_bindings_canonical_type_and_static_caller_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(source.payload(self.obj),source.payload(self.original))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),2)
        self.assertEqual(self.words[0],0x27BDFFC0)
        self.assertIn('s32 func_150490A8(struct17 *);',source.DECLARATIONS)
        self.assertEqual(self.helpers[source.ACOS][13:15],[0x97398E00,0x00194283])
        self.assertEqual(self.helpers[source.ACOS][6],0x3C01437F)
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        rom=self.values['conker/conker.us.bin'];opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],rom,entry-base+start)
            found.extend((row['function'],entry+i*4) for i,w in enumerate(words) if w==opcode)
        self.assertEqual(found,[('func_1511650C',0x1511654C)])
        self.assertEqual(struct.unpack_from('>12I',rom,0x1439D8),
            (0x920E004F,0x3C07800D,0x24E7C2D0,0x31CF0004,0x15E00003,0x2606007C,
             0x10000005,0x00002025,0x86040010,opcode,0x86050014,0x000220C3))
        self.assertIn('void *unused, void *actor',source.SELECTED)
        for entry,offset,count in source.HELPERS:
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,count*4)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+count*4],rom[offset:offset+count*4])
        self.receipt.update(all_direct_retail_call_sites=found,caller_223_words_static_only=True,
                            heading_return_bound_from_unsigned_table_and_branches=[0,255])

    def test_complete_model_reference_orders_wraps_late_reads_and_unwritten_middle(self):
        phases=0;fired=set();visits=set();angles=set()
        for case in self.cases:
            for phase in (0,8):
                expected,events,result,_,angle=reference(fixture(case,self.banks),case)
                a=self.run_model(self.truth,case,phase);b=self.run_model(self.words,case,phase)
                self.assertEqual(complete(a),complete(b));self.assertEqual(b.r[2],result)
                self.assertEqual(public_memory(b.memory),public_memory(expected))
                self.assertEqual([e for e in b.events if public_event(e)],events)
                self.assertEqual(b.middle,bytes(fixture(case,self.banks)[STACK+phase-64+0x20+i] for i in range(4)))
                visits.update(b.visits);fired.update(b.fired);angles.add(angle);phases+=1
        self.assertEqual(angles,set(range(256)))
        self.assertEqual(fired,{'actor-home-after-heading','actor-home-after-scale','finished-origin-and-unused-homes'})
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=visits)
        self.receipt.update(complete_final_states=phases,all_256_scale_arguments=True,
                            fired_physical_home_kinds=sorted(fired),retail_target_words_visited=39)

    def test_original_heading_lookup_scale_chain_with_actual_frozen_data(self):
        cases=[Case(bits(x),bits(z),heading=0) for x,z in itertools.product((-2.0,0.0,2.0),repeat=2)]
        cases += [Case(facing=i<<8|0xFF) for i in range(256)]
        cases += [c for c in self.cases if c.home or c.mutations]
        visits=set();count=0;lookup_entries=0;headings=set()
        for case in cases:
            for phase in (0,8):
                expected,events,result,_,_=reference(fixture(case,self.banks),case,connected=True)
                a=self.run_model(self.truth,case,phase,True);b=self.run_model(self.words,case,phase,True)
                self.assertEqual(complete(a),complete(b));self.assertEqual(b.r[2],result)
                self.assertEqual(public_memory(b.memory),public_memory(expected))
                self.assertEqual([e for e in b.events if public_event(e)],events)
                calls=[args for name,args in b.calls if name=='SCALE']
                self.assertEqual(len(calls),1)
                for address,data in self.banks.items():
                    self.assertEqual(bytes(b.memory[address+i] for i in range(len(data))),data)
                point=offset_bits(case);heading=original_heading(fixture(case,self.banks),point)
                self.assertTrue(0<=heading<=255);headings.add(heading)
                self.assertIn(source.HEADING,b.visits);self.assertIn(source.SCALE,b.visits);self.assertIn(source.SINE,b.visits)
                lookup_entries+=source.ACOS in b.visits;visits.update(b.visits);count+=1
        for entry,data in self.helpers.items():self.assertTrue(set(range(entry,entry+len(data)*4,4))<=visits)
        self.receipt.update(original_math_chain_phases=count,fired_original_lookup_entries=lookup_entries,
                            all_113_original_helper_words_visited=True,actual_frozen_math_data=True,
                            observed_heading_min=min(headings),observed_heading_max=max(headings),hardware_FCSR_modeled=False)

    def test_native32_three_optimizations_defined_fields_rounding_and_post_call_mutations(self):
        for optimization in ('-O0','-O2','-O3'):
            p=self.native(source.SELECTED,'native',optimization);self.assertEqual(p.returncode,0,(optimization,p.stderr))
        self.receipt.update(native_optimizations=3,trap_UBSan=True,native_middle_float_unread=True)

    def test_compiled_semantic_conversion_lookup_order_angle_scale_and_rounding_negatives(self):
        facing='    facing = *(u16 *)((u8 *)actor + 0x76);\n'
        early_facing=source.SELECTED.replace(facing,'').replace('    angle = func_150490A8(&offset);',
                                                              facing+'    angle = func_150490A8(&offset);')
        early_speed=source.SELECTED.replace('    scale = func_15048A40((u8)facing);\n    projected = *(f32 *)((u8 *)actor + 0x3C) * scale;',
            '    projected = *(f32 *)((u8 *)actor + 0x3C);\n    scale = func_15048A40((u8)facing);\n    projected *= scale;')
        negatives={
            'float-before-integer-difference':source.SELECTED.replace('offset.unk0 = (s32)((u32)actorX - (u32)originX)',
                'offset.unk0 = *(f32 *)((u8 *)actor + 0x14) - originX').replace('    s32 actorX = (s32)*(f32 *)((u8 *)actor + 0x14);\n',''),
            'wrong-z':source.SELECTED.replace('actor + 0x1C','actor + 0x14'),
            'early-facing':early_facing,'early-speed':early_speed,
            'low-facing-byte':source.SELECTED.replace('facing >> 8','facing & 255'),
            'wrong-heading-direction':source.SELECTED.replace('facing -= angle','facing += angle'),
            'next-scale-entry':source.SELECTED.replace('func_15048A40((u8)facing)','func_15048A40((u8)(facing + 1))'),
            'add-instead-of-multiply':source.SELECTED.replace('actor + 0x3C) * scale','actor + 0x3C) + scale'),
            'biased-truncation':source.SELECTED.replace('return (s32)projected','return (s32)(projected + 0.5f)'),
        }
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            p=self.native(body,'negative-'+name);self.assertEqual(p.returncode,23,(name,p.stderr))
        self.receipt['compiled_semantic_negatives']=len(negatives)

    def test_middle_zero_and_caching_actor_across_physical_home_changes_are_effective(self):
        zero=source.SELECTED.replace('    angle = func_150490A8(&offset);','    offset.unk4 = 0.0f;\n    angle = func_150490A8(&offset);')
        cached=source.SELECTED.replace('    struct17 offset;','    struct17 offset;\n    void *volatile cachedActor = actor;')
        cached=cached.replace('actor + 0x76','cachedActor + 0x76').replace('actor + 0x3C','cachedActor + 0x3C')
        for name,body,case in (('zero-middle',zero,Case()),('cached-actor',cached,Case(home=1,mutations=3))):
            obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+body,name)
            self.assertEqual(diagnostic,'')
            data,fs=source.link_owner(ROOT,self.output,obj,source.OWNER);raw,_=source.payload(obj)
            words=list(struct.unpack_from('>%dI'%(len(raw)//4),data,fs[source.FUNCTION]['value']))
            for phase,connected in itertools.product((0,8),(False,True)):
                a=self.run_model(self.truth,case,phase,connected);b=self.run_model(words,case,phase,connected)
                if name=='zero-middle':self.assertNotEqual(a.middle,b.middle)
                else:
                    self.assertIn('actor-home-after-heading',b.fired)
                    self.assertNotEqual([x for x in a.calls if x[0]=='SCALE'],[x for x in b.calls if x[0]=='SCALE'])
        self.receipt['effective_guest_negative_phases']=8

    def test_independent_GNU_code_helper_and_actor_rebases(self):
        count=0
        for i,(code_delta,helper_delta,data_delta) in enumerate(((0x10000,0x20000,0x3000),
                (0x100000,0x30000,-0x10000),(0x2000000,-0x10000,0x8000))):
            symbols={name:address+helper_delta for name,address in NAMES.items()};linked=[]
            for label,obj in (('C',self.obj),('original',self.original)):
                script=self.output/('rebase-%d-%s.ld'%(i,label))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+code_delta))
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                address,data=sections(elf)['.text'];self.assertEqual(address,source.ENTRY+code_delta)
                linked.append(list(struct.unpack('>39I',data[:156])))
            self.assertEqual(linked[0],linked[1])
            for case in (Case(),Case(*POSES[2],origin_x=0x80000000,origin_z=0x7FFFFFFF),
                         Case(mutations=3),Case(mutations=3,home=3)):
                for phase in (0,8):
                    a=self.run_model(linked[0],case,phase,False,data_delta,symbols,source.ENTRY+code_delta)
                    b=self.run_model(linked[1],case,phase,False,data_delta,symbols,source.ENTRY+code_delta)
                    self.assertEqual(complete(a),complete(b))
                    expected,_,result,_,_=reference(fixture(case,self.banks,data_delta),case,data_delta)
                    self.assertEqual(a.r[2],result);self.assertEqual(public_memory(a.memory,data_delta),public_memory(expected,data_delta))
                    count+=1
        self.receipt.update(independent_GNU_rebase_plans=3,rebased_phases=count)

    def test_actual_owner_Make_live_history_and_strict_first_image(self):
        report=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((report['preserved_neighbors'],report['relocations']),(83,2))
        make=json.loads((self.output/'make-shadow.json').read_text());self.assertEqual(make['actual_Make_commands'],5)
        before=self.values['conker/build/conker.us.elf'];actual=(self.output/'first-linked.elf').read_bytes()
        truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+156]
        source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,156)
        size=next(offset+8 for offset,name,_,_ in source.symbol_rows(before) if name==source.FUNCTION)
        for offset in (0,at-1,at,at+155,at+156,size+3):
            wrong=bytearray(actual);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        for wrong in (actual[:-1],actual+b'\0'):
            with self.assertRaises(ValueError):source.check_image(before,wrong,truth)
        if self.installed:self.assertTrue(source.audit(ROOT,self.output)['strict_first_link_reproduced'])
        else:
            for name,value in self.values.items():self.assertEqual((ROOT/name).read_bytes(),value,name)
        self.receipt.update(preserved_neighbors=83,wrong_image_controls=8)


if __name__=='__main__':
    unittest.main()
