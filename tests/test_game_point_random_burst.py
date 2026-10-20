"""Direct random-burst C, independent packets, native32 and bounded caller ABI."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_point_random_burst as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
POINT, OTHER = 0x28000, 0x29000
COORDS = (0.0, -0.0, 1.75, -2.75, 32768.25, -65536.5, 1e20, -1e20)


@dataclass(frozen=True)
class Case:
    rng: int = 0xFFFFFFFF
    random: int = bits(0.5)
    point: tuple = (bits(1.75), bits(-2.75), bits(32768.25))
    mutation: int = 0
    home: bool = False


def corpus():
    for i in range(256):
        yield Case((i * 1664525 + 1013904223) & 0xFFFFFFFF, bits((i % 65) / 64),
                   tuple(bits(COORDS[(i+j) % len(COORDS)]) for j in range(3)), i % 4)
    for rng, random, mode in itertools.product(
            (0, 1, 20, 21, 22, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF),
            (0, 1, 0x3EFFFFFF, 0x3F000000, 0x3F7FFFFF, 0x3F800000, bits(-0.25), bits(1e20)),
            (0, 3)):
        yield Case(rng, random, mutation=mode)
    for remainder in range(21):
        yield Case(21 * 0x0C30C30B + remainder, bits(remainder / 20), mutation=remainder % 4)
    yield Case(home=True)
    yield Case(home=True, mutation=3)


def final_point(case):
    if case.home:
        return tuple(bits(700.0+i) for i in range(3))
    if case.mutation & 2:
        return tuple(bits(200.0+i) for i in range(3))
    if case.mutation & 1:
        return tuple(bits(100.0+i) for i in range(3))
    return case.point


def packet(case):
    scaled = bits(floating(case.random) * 59.0)
    scale = bits(floating(scaled) + 170.0)
    return (*final_point(case), scale, 0, 255, case.rng % 21 + 10, 0x13, 0, 0, 0, 255)


def fixture(case, phase=0, point=POINT):
    memory = {STACK+i: (i*17+0xA5)&255 for i in range(-0x500, 0x200)}
    for base in (point, OTHER):
        memory.update({base+i: 0xA5 for i in range(-16, 28)})
    for i, word in enumerate(case.point):
        put(memory, point+i*4, word)
    for i in range(3):
        put(memory, OTHER+i*4, bits(700.0+i))
    return memory


class CallerBoundary(Exception):
    pass


class ReturnBoundaryCode:
    def __init__(self, code, boundary, owner):
        self.code, self.boundary, self.owner = code, boundary, owner

    def __contains__(self, address):
        return address == self.boundary or address in self.code

    def __getitem__(self, address):
        if address == self.boundary:
            self.owner.boundary_hit = address
            raise CallerBoundary
        return self.code[address]


class BurstOracle(TimingOracle):
    def __init__(self, words, case, phase=0, delta=0, entry=source.ENTRY, connected=None):
        self.case, self.delta, self.packets = case, delta, []
        self.caller = entry in (source.CALLSITE, 0x150287E8)
        offset = 0x15C if entry == source.CALLSITE else 0x4F8
        self.point = STACK+phase+offset if self.caller else POINT
        self.target_sp = STACK+phase
        super().__init__(words, fixture(case, phase, self.point), phase=phase, entry=entry,
                         arguments=(self.point,), connected=connected)
        self.boundary_hit = None
        if self.caller:
            boundary = 0x150CA880 if entry == source.CALLSITE else 0x150287F8
            self.code = ReturnBoundaryCode(self.code, boundary, self)
            self.f[18], self.f[10] = case.point[1:]

    def record_call(self, target):
        if target == source.ENTRY:
            assert self.r[4] == self.point
            self.calls.append(('ENTER', (self.r[4],)))
            return
        if target == source.SUBMIT+self.delta:
            args = (self.f[12], self.f[14], self.r[6], self.r[7],
                    *(self.get(self.r[29]+0x10+i*4, 4) for i in range(8)))
            self.packets.append(args)
        elif target in (source.INTEGER_RNG+self.delta, source.FLOAT_RNG+self.delta):
            args = ()
        else:
            raise AssertionError(('Unknown burst provider', hex(target)))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678

    def hook(self, target):
        if target == source.INTEGER_RNG+self.delta and self.case.mutation & 1:
            for i in range(3):
                self.put(self.point+i*4, bits(100.0+i), 4)
        if target == source.FLOAT_RNG+self.delta:
            if self.case.mutation & 2:
                for i in range(3):
                    self.put(self.point+i*4, bits(200.0+i), 4)
            if self.case.home:
                self.put(self.target_sp, OTHER, 4)
        self.clobber()
        if target == source.INTEGER_RNG+self.delta:
            self.r[2] = self.case.rng
        elif target == source.FLOAT_RNG+self.delta:
            self.f[0] = self.case.random
        else:
            self.r[2] = 0x76543210


def native_harness(body, cases):
    rows = ['{'+','.join('0x%Xu' % v for v in
            (c.rng, c.random, *c.point, c.mutation))+',{'+
            ','.join('0x%Xu' % v for v in packet(c))+'}}' for c in cases]
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef short s16;typedef float f32;
typedef struct{f32 unk0,unk4,unk8;}struct17;
''' + source.DECLARATIONS.replace('#include "structs.h"', '') + body + '''
typedef struct{u32 rng,random,x,y,z,mode,expected[12];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct{u32 before[4];struct17 point;u32 after[4];}storage;
static int calls,error;static u32 outputs[12];
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
s32 func_150ADA20(void){
    union{u32 u;s32 s;}v;
    if(calls++!=0)error=1;
    if(item->mode&1){storage.point.unk0=100.0f;storage.point.unk4=101.0f;storage.point.unk8=102.0f;}
    v.u=item->rng;return v.s;
}
f32 func_150ADA68(void){
    if(calls++!=1)error=1;
    if(item->mode&2){storage.point.unk0=200.0f;storage.point.unk4=201.0f;storage.point.unk8=202.0f;}
    return real(item->random);
}
void func_1514C678(f32 x,f32 y,f32 z,f32 scale,s16 low,s16 high,s16 count,u8 kind,s32 flags,f32 extra,void *data,u8 alpha){
    u32 i;
    if(calls++!=2)error=1;
    outputs[0]=word(x);outputs[1]=word(y);outputs[2]=word(z);outputs[3]=word(scale);
    outputs[4]=(u32)low;outputs[5]=(u32)high;outputs[6]=(u32)count;outputs[7]=kind;
    outputs[8]=(u32)flags;outputs[9]=word(extra);outputs[10]=(u32)data;outputs[11]=alpha;
    for(i=0;i<12;i++)if(outputs[i]!=item->expected[i])error=1;
}
static int test_all(void){
    u32 n,i;
    if(sizeof(struct17)!=12 || __builtin_offsetof(struct17,unk4)!=4 || __builtin_offsetof(struct17,unk8)!=8)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<4;i++){storage.before[i]=0xA5A5A5A5u;storage.after[i]=0xA5A5A5A5u;}
        storage.point.unk0=real(item->x);storage.point.unk4=real(item->y);storage.point.unk8=real(item->z);
        func_150CA930(&storage.point);
        if(error || calls!=3)return 23;
        for(i=0;i<4;i++)if(storage.before[i]!=0xA5A5A5A5u || storage.after[i]!=0xA5A5A5A5u)return 24;
        if(word(storage.point.unk0)!=item->expected[0] || word(storage.point.unk4)!=item->expected[1] ||
           word(storage.point.unk8)!=item->expected[2])return 25;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class PointRandomBurstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT/source.BUILD
        cls.installed = source.digest((ROOT/source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            source.freeze(ROOT, cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT, cls.output);source.make_shadow(ROOT, cls.output);source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output)
        cls.obj, diagnostic = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED, 'fresh-selected')
        if diagnostic:
            raise ValueError(diagnostic)
        data, funcs = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>40I', data, funcs[source.FUNCTION]['value']))
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>40I', cls.rom, source.ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if not c.home]
        cls.receipt = dict(installed=cls.installed, cases=len(cls.cases),
                           native_cases=len(cls.native_cases), guards=0, matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt, indent=2)+'\n')
        print('point random burst qualification:', cls.receipt)

    def test_01_direct_words_three_calls_canonical_point_and_complete_helper_inspection(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual(source.payload(self.obj), source.payload(source.original(ROOT, self.output)))
        self.assertEqual(sum(map(len, source.payload(self.obj)[1].values())), 3)
        self.assertEqual(self.words[10], 0xA7AF003E)
        self.assertEqual(self.words[20], 0x87B9003E)
        helper = struct.unpack_from('>120I', self.rom, 0x179B28)
        self.assertEqual(helper[21:24], (0x87A400B6, 0x87A500B2, 0x0085082A))
        self.assertIn(0x93AA00BF, helper)
        self.assertIn(0xC7BE00C4, helper)
        self.assertIn(0x8FB700C8, helper)
        self.assertIn(0x93BE00CF, helper)
        check = source.DECLARATIONS+'''
typedef char point_size[sizeof(struct17)==12?1:-1];
typedef char point_y[(u32)&((struct17 *)0)->unk4==4?1:-1];
typedef char point_z[(u32)&((struct17 *)0)->unk8==8?1:-1];
'''+source.SELECTED
        obj, diagnostic = source.compile_owner(ROOT, self.output, '#include <ultra64.h>\n'+check, 'canonical-point')
        self.assertEqual(diagnostic, '')
        self.assertEqual(source.payload(obj), source.payload(self.obj))

    def test_02_complete_models_reference_rng_order_reads_count_and_all_words(self):
        visits, counts = set(), set()
        for case, phase in itertools.product(self.cases, (0, 8)):
            a = BurstOracle(self.truth, case, phase).run()
            b = BurstOracle(self.words, case, phase).run()
            self.assertEqual(complete(a), complete(b))
            self.assertEqual(b.packets, [packet(case)])
            self.assertEqual([c[0] for c in b.calls], [source.INTEGER_RNG, source.FLOAT_RNG, source.SUBMIT])
            expected_point = OTHER if case.home else POINT
            reads = [e for e in b.events if e[0]=='R' and e[1] in
                     {base+i*4 for base in (POINT, OTHER) for i in range(3)}]
            self.assertEqual(reads, [('R', expected_point+i*4, 4, w) for i,w in enumerate(final_point(case))])
            last_rng = next(i for i,e in enumerate(b.events) if e[:2]==('CALL', source.FLOAT_RNG))
            self.assertTrue(all(i>last_rng for i,e in enumerate(b.events) if e in reads))
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg], b.before[reg])
            self.assertEqual(b.f[20:], b.saved_f)
            visits.update(b.visits);counts.add(b.packets[0][6])
        self.assertTrue(set(range(source.ENTRY, source.ENTRY+160, 4))<=visits)
        self.assertEqual(counts, set(range(10,31)))
        self.receipt.update(full_model_phases=len(self.cases)*2, all40_words_visited=True,
            count_range=[10,30], unsigned_full_word_RNG=True, float32_two_rounding_steps=True,
            late_point_reads=True, incoming_home_redirects_guest_only=2)

    def native(self, body, label, optimization='-O2'):
        unit = self.output/(label+'.c');unit.write_text(native_harness(body, self.native_cases))
        binary = self.output/(label+optimization)
        args = ['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p = subprocess.run(args, capture_output=True, text=True)
        (self.output/(label+optimization+'-compiler.log')).write_text(p.stdout+p.stderr)
        self.assertEqual(p.returncode, 0, p.stderr[:6000])
        return subprocess.run([str(binary)], capture_output=True, timeout=30).returncode

    def test_03_native32_three_optimizations_and_effective_compiled_semantic_negatives(self):
        for optimization in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED, 'native', optimization), 0)
        controls = {
            'signed-rng': source.SELECTED.replace('(u32)func_150ADA20() % 21U', 'func_150ADA20() % 21'),
            'wrong-modulus': source.SELECTED.replace('% 21U', '% 22U'),
            'wrong-base': source.SELECTED.replace('+ 10;', '+ 11;'),
            'wrong-scale': source.SELECTED.replace('59.0f', '58.0f'),
            'wrong-offset': source.SELECTED.replace('170.0f', '171.0f'),
            'wrong-x': source.SELECTED.replace('point->unk0,', 'point->unk4,'),
            'wrong-type': source.SELECTED.replace('count, 0x13', 'count, 0x14'),
            'wrong-count': source.SELECTED.replace('255, count,', '255, count + 1,'),
            'wrong-alpha': source.SELECTED.replace('0.0f, 0, 255', '0.0f, 0, 254'),
            'early-point': source.SELECTED.replace('    s16 count =', '    struct17 early = *point;\n    s16 count =').replace('point->unk','early.unk'),
        }
        for label, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            self.assertEqual(self.native(body, label), 23, label)
        self.receipt.update(native_optimizations=3, trap_UBSan=True, compiled_semantic_negatives=len(controls))

    def test_04_effective_guest_unsigned_divide_and_short_home_negatives(self):
        for index, word in ((6, 0x0041001A), (10, 0xA7AF003C)):
            bad = self.words.copy();bad[index] = word
            actual = BurstOracle(bad, Case()).run()
            self.assertNotEqual(actual.packets, [packet(Case())])
        self.receipt['effective_guest_negatives'] = 2

    def test_05_direct_caller_inventory_and_real_forwarding_window(self):
        symbols = load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows = list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows, 'us', DEFAULT_SEGMENTS['us'], symbols)
        opcode = 0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found = []
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:
                continue
            base,start = DEFAULT_SEGMENTS['us'][row['section']];entry = function_vram(row,symbols)
            words = struct.unpack_from('>%dI'%row['_retail_nwords'], self.rom, entry-base+start)
            found.extend((row['function'],entry+i*4) for i,w in enumerate(words) if w==opcode)
        self.assertEqual(found, [('func_150265CC',0x150287F0),('func_150CA150',source.CALLSITE)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY) for i in range(0,len(self.rom),4)))
        windows = [(source.CALLSITE,list(struct.unpack_from('>2I',self.rom,0xF7D28)),0x150CA880),
                   (0x150287E8,list(struct.unpack_from('>4I',self.rom,0x55C98)),0x150287F8)]
        self.assertEqual(windows[0][1], [opcode,0x27A4015C])
        self.assertEqual(windows[1][1], [0x27A404F8,0xE7B204FC,opcode,0xE7AA0500])
        phases = 0
        for case, phase, (entry,window,boundary) in itertools.product(self.native_cases[::31], (0,8), windows):
            models = []
            for code in (self.truth,self.words):
                connected = dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                model = BurstOracle(window,case,phase,entry=entry,connected=connected)
                with self.assertRaises(CallerBoundary):
                    model.run()
                self.assertEqual(model.boundary_hit,boundary)
                self.assertEqual(model.packets, [packet(case)])
                self.assertEqual(model.r[29],STACK+phase)
                models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(all_direct_retail_call_sites=found, actual_caller_window_phases=phases,
            actual_post_return_boundaries=phases*2, full_caller_execution_claimed=False,
            downstream_helper_execution_claimed=False)

    def test_06_independent_GNU_call_rebases(self):
        count = 0
        for delta in (0x10000,0xCF20,0x18000):
            images = []
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf,script = self.output/('rebase-%d-%d.elf'%(delta,i)),self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                definitions = ['--defsym=%s=0x%X'%(name,address+delta) for name,address in (
                    ('func_150ADA20',source.INTEGER_RNG),('func_150ADA68',source.FLOAT_RNG),('func_1514C678',source.SUBMIT))]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *definitions,'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::29]:
                model = BurstOracle(images[0],case,delta=delta).run()
                self.assertEqual(model.packets,[packet(case)]);count+=1
        self.receipt.update(independent_rebase_phases=count,rebase_sets=3)

    def test_07_strict_image_header_code_data_metadata_and_length_negatives(self):
        before = self.values['conker/build/conker.us.elf']
        truth = self.rom[source.ROM:source.ROM+160]
        predicted = source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets = (20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted) if name==source.FUNCTION))
        for at in offsets:
            bad = bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_negative_controls'] = 7
