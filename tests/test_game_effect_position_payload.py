"""Coordinate snapshot, saved-S0 lifetime and bounded original caller qualification."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_effect_position_payload as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK


ROOT = Path(__file__).resolve().parents[2]
ACTOR, EFFECT = 0x28000, 0x30000
NAMES = {'func_15149130': source.SPAWN, 'memcpy': source.COPY,
         'func_15083E90': source.LOOKUP, 'func_150F0BEC': source.INIT,
         'func_15161E24': source.FOLLOW}
POINTS = ((0, 0x80000000, 0x3F800000), (0xBF800000, 0x41280000, 0xC3400000),
          (0x7F7FFFFF, 0xFF7FFFFF, 0x00800000),
          (0x7F800000, 0xFF800000, 0x7FC12345),
          (0x7FA12345, 0xFFC12345, 1))
INITIALIZED = (0x40000000, 0xC0600000, 0x40880000)
MUTATED = (0x42C80000, 0xC3480000, 0x43960000)
FOLLOWED = (0x41000000, 0xC1800000, 0x42000000)


@dataclass(frozen=True)
class Case:
    byte: int = 0xA7
    point: tuple = POINTS[0]
    allocated: bool = True
    mutations: int = 0
    padding_alias: bool = False
    source_home: bool = False
    destination: int = 0
    wrapper: bool = False
    lookup: bool = True
    seed: int = 0xA5


def corpus():
    for i, (byte, point, allocated, mutations) in enumerate(itertools.product(
            (0, 127, 128, 255), POINTS, (False, True), (0, 2))):
        yield Case(byte, point, allocated, mutations, seed=i * 31 & 255)
    for allocated, mutations, lookup in itertools.product((False, True), range(8), (False, True)):
        yield Case(0x7B, POINTS[1], allocated, mutations, wrapper=True, lookup=lookup)
    for destination, padding, home, seed in itertools.product(range(4), (False, True), (False, True), (0xA5, 0x5A)):
        yield Case(255, POINTS[2], mutations=2, destination=destination,
                   padding_alias=padding, source_home=home, seed=seed)


def fixture(case, delta=0):
    memory = {STACK + i: (i * 17 + case.seed) & 255 for i in range(-0x400, 0x100)}
    for base in (ACTOR + delta, EFFECT + delta):
        memory.update({base + i: (i * 11 + 0x35) & 255 for i in range(256)})
    put(memory, ACTOR + delta + 0x3B, case.byte, 1)
    for i, value in enumerate(case.point):
        put(memory, ACTOR + delta + 0x14 + i * 4, value)
    return memory


def public_event(event, delta=0):
    if event[0] == 'CALL':
        return event[1] != 'ENTER'
    return any(base <= event[1] < base + 256 for base in (ACTOR + delta, EFFECT + delta))


def public_memory(memory, delta=0):
    return {a: v for a, v in memory.items()
            if any(base <= a < base + 256 for base in (ACTOR + delta, EFFECT + delta))}


def destination(case, payload, delta=0):
    return (EFFECT + delta + 0x28 if case.destination == 0 else ACTOR + delta + 0x37
            if case.destination == 1 else payload + (1 if case.destination == 2 else -1))


def captured(case):
    return (0x19, INITIALIZED) if case.wrapper and case.mutations & 1 else (case.byte, case.point)


def reference(initial, case, phase=0, delta=0):
    memory, events = initial.copy(), []
    entered = STACK + phase - (56 if case.wrapper else 0)
    payload, actor = entered - 88 + 0x40, ACTOR + delta

    def store(address, value, size):
        put(memory, address, value, size)
        events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    def change(byte, point):
        store(actor + 0x3B, byte, 1)
        for i, value in enumerate(point):
            store(actor + 0x14 + i * 4, value, 4)

    if case.wrapper:
        events.append(('CALL', 'LOOKUP', (18,)))
        if not case.lookup:
            return memory, events
        events.append(('CALL', 'INIT', (actor,)))
        if case.mutations & 1:
            change(0x19, INITIALIZED)
    events.append(('R', actor + 0x3B, 1, memory[actor + 0x3B]))
    put(memory, payload, actor)
    put(memory, payload + 4, memory[actor + 0x3B], 1)
    put(memory, payload + 8, 0)
    for i in range(3):
        at = actor + 0x14 + i * 4
        value = read(memory, at)
        events.append(('R', at, 4, value))
        put(memory, payload + 12 + i * 4, value)
    events.append(('CALL', 'SPAWN', (300, 0xFFFFFFFF, 0x4C, 0xFFFFFFFF, 0, 0x3A, 24, 0xFF, 1)))
    if case.mutations & 2:
        change(0xC3, MUTATED)
    if case.padding_alias:
        for i, value in enumerate((0x11, 0x22, 0x33)):
            put(memory, payload + 5 + i, value, 1)
    if case.allocated:
        target = destination(case, payload, delta)
        events.append(('CALL', 'COPY', (target, 'payload', 24)))
        for i in range(24):
            store(target + i, memory[payload + i], 1)
    if case.wrapper:
        events.append(('CALL', 'FOLLOW', (actor, 1, 2, 300, 70, 255, 130, 0, 255, 1)))
        if case.mutations & 4:
            change(0xE7, FOLLOWED)
    return memory, [e for e in events if public_event(e, delta)]


class PositionOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0, delta=0, symbols=None,
                 entry=source.ENTRY, connected=None, arguments=None):
        self.case, self.delta = case, delta
        self.by_address = {v: k for k, v in (symbols or NAMES).items()}
        self.main_sp_entry = STACK + phase
        self.padding_observed, self.snapshot, self.fired = None, None, []
        args = (ACTOR + delta,) if arguments is None else arguments
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=connected)

    def record_call(self, target):
        if target == source.ENTRY:
            self.main_sp_entry = self.r[29]
            self.calls.append(('ENTER', self.arguments(1)))
            self.events.append(('CALL', 'ENTER', self.arguments(1)))
            return
        name = self.by_address[target]
        label = {'func_15149130': 'SPAWN', 'memcpy': 'COPY', 'func_15083E90': 'LOOKUP',
                 'func_150F0BEC': 'INIT', 'func_15161E24': 'FOLLOW'}[name]
        args = self.arguments({'SPAWN': 9, 'COPY': 3, 'LOOKUP': 1, 'INIT': 1, 'FOLLOW': 10}[label])
        if label in ('SPAWN', 'COPY'):
            assert self.r[16] == ACTOR + self.delta, ('saved source lifetime', self.r[16])
        if label == 'SPAWN':
            at = self.main_sp_entry - 88 + 0x40
            self.snapshot = bytes(self.memory[at + i] for i in range(24))
        if label == 'COPY':
            self.padding_observed = bytes(self.memory[args[1] + i] for i in range(5, 8))
            args = (args[0], 'payload', args[2])
        self.calls.append((label, args))
        self.events.append(('CALL', label, args))

    def change(self, byte, point):
        actor = ACTOR + self.delta
        self.put(actor + 0x3B, byte, 1)
        for i, value in enumerate(point):
            self.put(actor + 0x14 + i * 4, value, 4)

    def hook(self, target):
        name = self.by_address[target]
        if name == 'func_15083E90':
            result = ACTOR + self.delta if self.case.lookup else 0
        elif name == 'func_150F0BEC':
            if self.case.mutations & 1:
                self.change(0x19, INITIALIZED)
            result = 0x13572468
        elif name == 'func_15161E24':
            if self.case.mutations & 4:
                self.change(0xE7, FOLLOWED)
            result = 0x24681357
        elif name == 'func_15149130':
            if self.case.mutations & 2:
                self.change(0xC3, MUTATED)
            if self.case.padding_alias:
                for i, value in enumerate((0x11, 0x22, 0x33)):
                    self.put(self.main_sp_entry - 88 + 0x45 + i, value, 1)
                self.fired.append('payload-reserved')
            if self.case.source_home:
                self.put(self.main_sp_entry, 0xFEDCBA98, 4)
                self.fired.append('source-home')
            result = destination(self.case, self.main_sp_entry - 88 + 0x40, self.delta) - 0x28 if self.case.allocated else 0
        else:
            dst, src, length = self.arguments(3)
            for i in range(length):
                self.put(dst + i, self.get(src + i, 1), 1)
            result = dst
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = result


def complete(model):
    return model.r, model.f, model.hi, model.lo, model.condition, model.memory, model.events, model.calls, model.visits


def native_harness(body, cases, wrapper):
    rows = ['{%d,{0x%Xu,0x%Xu,0x%Xu},%d,%d,%d,%d}' %
            (c.byte, *c.point, c.allocated, c.mutations, c.wrapper, c.lookup) for c in cases]
    return '''typedef unsigned int u32; typedef int s32; typedef unsigned char u8;
typedef signed char s8; typedef short s16; typedef float f32;
#define NULL ((void *)0)
''' + source.DECLARATIONS + '''
typedef char payload_size_is_24[sizeof(EffectPositionPayload)==24 ? 1 : -1];
''' + body + '''
typedef struct {u8 prefix[20]; f32 position[3]; u8 middle[27]; u8 sourceByte; u8 suffix[196];} struct127;
static struct127 actor;
static u8 effect[256];
struct127 *func_15083E90(s32);
void func_150F0BEC(struct127 *);
void func_15161E24(struct127 *,s32,s32,s32,s32,s32,s32,s32,s32,s32);
''' + wrapper + '''
typedef struct {int byte;u32 point[3];int allocated,mutations,wrapper,lookup;} Case;
static const Case cases[]={
''' + ',\n'.join(rows) + '''
};
static const Case *item;
static int stage,error,copies;
static u32 word(f32 f) {union {f32 f;u32 u;} v;v.f=f;return v.u;}
static f32 real(u32 u) {union {f32 f;u32 u;} v;v.u=u;return v.f;}
static void copy_bytes(void *d,const void *s,u32 n) {
    u8 *dst=d;const u8 *src=s;while(n--)*dst++=*src++;
}
static void change(u8 byte,const u32 *point) {
    int i;actor.sourceByte=byte;for(i=0;i<3;i++)actor.position[i]=real(point[i]);
}
static const u32 initialized[3]={0x40000000u,0xC0600000u,0x40880000u};
static const u32 mutated[3]={0x42C80000u,0xC3480000u,0x43960000u};
static const u32 followed[3]={0x41000000u,0xC1800000u,0x42000000u};
struct127 *func_15083E90(s32 id) {
    if(stage++!=0 || id!=18)error=1;
    return item->lookup ? &actor : NULL;
}
void func_150F0BEC(struct127 *p) {
    if(stage++!=1 || p!=&actor)error=1;
    if(item->mutations&1)change(0x19,initialized);
}
void func_15161E24(struct127 *p,s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,s32 i) {
    if(stage++!=(item->allocated?4:3) || p!=&actor || a!=1 || b!=2 || c!=300 ||
       d!=70 || e!=255 || f!=130 || g!=0 || h!=255 || i!=1)error=1;
    if(item->mutations&4)change(0xE7,followed);
}
void *func_15149130(s16 life,s8 a,s8 b,s8 c,u8 flags,u8 kind,s32 size,u8 variant,s32 parameter) {
    if(stage++!=(item->wrapper?2:0) || life!=300 || a!=-1 || b!=0x4C || c!=-1 ||
       flags!=0 || kind!=0x3A || size!=24 || variant!=255 || parameter!=1)error=1;
    if(item->mutations&2)change(0xC3,mutated);
    return item->allocated ? effect : NULL;
}
void *memcpy(void *dst,const void *src,u32 size) {
    const EffectPositionPayload *p=src;int i;
    const u32 *point=(item->wrapper && (item->mutations&1)) ? initialized : item->point;
    int byte=(item->wrapper && (item->mutations&1)) ? 0x19 : item->byte;
    if(stage++!=(item->wrapper?3:1) || !item->allocated || dst!=effect+0x28 || size!=24) {
        error=1;return dst;
    }
    if(p->source!=&actor || p->sourceByte!=byte || word(p->value)!=0)error=1;
    for(i=0;i<3;i++)if(word(p->position[i])!=point[i])error=1;
    copy_bytes(dst,src,size);copies++;
    return dst;
}
static int test_all(void) {
    u32 c,i;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        EffectPositionPayload decoded;
        item=&cases[c];stage=error=copies=0;
        for(i=0;i<256;i++)((u8 *)&actor)[i]=effect[i]=0xA5;
        change((u8)item->byte,item->point);
        if(item->wrapper)func_15071764(0x12345678);
        else func_150F10D4(&actor);
        if(item->wrapper && !item->lookup) {
            if(error || stage!=1 || copies!=0)return 23;
        } else {
            if(error || stage!=(item->wrapper?(item->allocated?5:4):(item->allocated?2:1)) ||
               copies!=item->allocated)return 23;
            if(item->allocated) {
                const u32 *point=(item->wrapper && (item->mutations&1)) ? initialized : item->point;
                int byte=(item->wrapper && (item->mutations&1)) ? 0x19 : item->byte;
                copy_bytes(&decoded,effect+0x28,24);
                if(decoded.source!=&actor || decoded.sourceByte!=byte || word(decoded.value)!=0)return 24;
                for(i=0;i<3;i++)if(word(decoded.position[i])!=point[i])return 24;
            }
        }
        for(i=0;i<256;i++) {
            int output=item->allocated && (!item->wrapper || item->lookup) && i>=0x28 && i<0x40;
            if(!output && effect[i]!=0xA5)return 25;
            if(!(i>=0x14 && i<0x20) && i!=0x3B && ((u8 *)&actor)[i]!=0xA5)return 26;
        }
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=test_all();
    __asm__ volatile("int $0x80" : : "a"(1),"b"(status) : "memory");
    __builtin_unreachable();
}
'''


class EffectPositionPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.installed = source.digest((ROOT / source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            source.qualify(ROOT, cls.output)
            source.make_shadow(ROOT, cls.output)
            source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output)
        cls.obj, diagnostic = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n' + source.DECLARATIONS + source.SELECTED, 'fresh-selected')
        if diagnostic:
            raise ValueError(diagnostic)
        cls.original = source.original(ROOT, cls.output)
        text, functions = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>39I', text, functions[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>39I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.copy_words = list(struct.unpack_from('>11I', cls.values['conker/conker.us.bin'], 0x22EC0))
        cls.caller_words = list(struct.unpack_from('>31I', cls.values['conker/conker.us.bin'], source.CALLER_ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if not c.padding_alias and not c.source_home and c.destination==0
                            and all(v & 0x7F800000 != 0x7F800000 for v in c.point)]
        caller_source = cls.values[source.CALLER].decode()
        lo, hi = source.function_span(caller_source, 'func_15071764')
        cls.wrapper = caller_source[lo:hi]
        cls.receipt = dict(cases=len(cls.cases),native_cases=len(cls.native_cases),
            installed=cls.installed,matching_credit=int(cls.installed),compiler_only=True,guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('effect position qualification:',cls.receipt)

    def run_model(self, words, case, phase=0, connected_copy=False, delta=0, symbols=None, entry=source.ENTRY):
        connected = {}
        if connected_copy:
            at = (symbols or NAMES)['memcpy']
            connected.update(zip(range(at,at+44,4),self.copy_words))
        if case.wrapper:
            connected.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
            return PositionOracle(self.caller_words,fixture(case,delta),case,phase,delta,symbols,
                source.CALLER_ENTRY,connected,(0x12345678,)).run()
        return PositionOracle(words,fixture(case,delta),case,phase,delta,symbols,entry,connected).run()

    def native(self, body, label, optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases,self.wrapper))
        binary=self.output/(label+optimization)
        command=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
            str(unit),'-o',str(binary)]
        process=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        return subprocess.run([str(binary)],capture_output=True,timeout=30)

    def test_direct_complete_C_original_bindings_and_all_direct_retail_callers(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(self.original))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),2)
        self.assertEqual(self.words[0],0x27BDFFA8)
        self.assertEqual(self.words[27:29],[0x0D45244C,0xE7AA0054])
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000 | (source.ENTRY>>2 & 0x3FFFFFF)
        found=[]
        rom=self.values['conker/conker.us.bin']
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:continue
            vram,rom_start=DEFAULT_SEGMENTS['us'][row['section']]
            entry=function_vram(row,symbols);offset=entry-vram+rom_start
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],rom,offset)
            found.extend((row['function'],entry+i*4) for i,w in enumerate(words) if w==opcode)
        self.assertEqual(found,[('func_15071764',0x15071788)])
        self.assertEqual(self.caller_words[0],0x27BDFFC8)
        self.assertEqual(self.caller_words[9:12],[opcode,0x8FA40034,0x240E0046])
        self.assertEqual(self.caller_words[-4:], [0x8FBF002C,0x27BD0038,0x03E00008,0])
        self.receipt['all_direct_retail_call_sites']=found

    def test_full_model_reference_captures_saved_register_reserved_bytes_and_retail_memcpy(self):
        visits=set();phases=0;fired=set();connected=0;configured=0;wrappers=0;targets=0
        for case in self.cases:
            for phase in (0,8):
                expected,events=reference(fixture(case),case,phase)
                for copy in (False,True):
                    a=self.run_model(self.truth,case,phase,copy)
                    b=self.run_model(self.words,case,phase,copy)
                    self.assertEqual(complete(a),complete(b))
                    self.assertEqual(public_memory(b.memory),public_memory(expected),case)
                    self.assertEqual([event for event in b.events if public_event(event)],events,(case,copy))
                    entered=not case.wrapper or case.lookup
                    if entered:
                        byte,point=captured(case)
                        self.assertEqual(struct.unpack_from('>I',b.snapshot)[0],ACTOR)
                        self.assertEqual(b.snapshot[4],byte)
                        self.assertEqual(struct.unpack_from('>4I',b.snapshot,8),(0,*point))
                        targets+=1
                    if entered and case.allocated:
                        payload=b.main_sp_entry-88+0x40
                        wanted=bytes((0x11,0x22,0x33)) if case.padding_alias else bytes(fixture(case)[payload+i] for i in range(5,8))
                        self.assertEqual(b.padding_observed,wanted)
                    fired.update(b.fired);visits.update(b.visits);phases+=1;configured+=copy
                    entered_copy=source.COPY in b.visits
                    self.assertEqual(entered_copy,bool(copy and entered and case.allocated))
                    connected+=entered_copy
                    if case.wrapper:
                        self.assertIn(source.CALLER_ENTRY,b.visits)
                        self.assertEqual(source.ENTRY in b.visits,case.lookup)
                        wrappers+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=visits)
        self.assertEqual(fired,{'source-home','payload-reserved'})
        self.receipt.update(model_variant_phases=phases,complete_final_states=phases,
            connected_original_memcpy_phases=connected,retail_target_words_visited=39,
            configured_memcpy_phases=configured,original_C_wrapper_phases=wrappers,
            fired_target_phases=targets,fired_physical_alias_kinds=sorted(fired),
            hardware_FCSR_modeled=False,nonfinite_patterns_guest_only=True)

    def test_native32_three_optimizations_valid_actor_fields_and_complete_C_wrapper(self):
        for optimization in ('-O0','-O2','-O3'):
            result=self.native(source.SELECTED,'native',optimization)
            self.assertEqual(result.returncode,0,(optimization,result.stdout,result.stderr))
        self.receipt.update(native_optimizations=3,trap_UBSan=True,
            native_reserved_bytes_unconstrained=True,native_typed_actor_float_subobjects=True)

    def test_compiled_semantic_capture_coordinates_flags_size_destination_and_copy_negatives(self):
        assignment='\n'.join('    payload.position[%d] = *(f32 *)((u8 *)source + 0x%X);'%(i,0x14+i*4) for i in range(3))+'\n'
        late=source.SELECTED.replace(assignment,'').replace('    if (effect != 0) {',assignment+'    if (effect != 0) {')
        negatives={
            'late-position-capture':late,
            'wrong-x':source.SELECTED.replace('source + 0x14','source + 0x18'),
            'wrong-z':source.SELECTED.replace('source + 0x1C','source + 0x18'),
            'wrong-flags':source.SELECTED.replace('0, 0x3A, 24','1, 0x3A, 24'),
            'wrong-payload-size':source.SELECTED.replace('0x3A, 24','0x3A, 12'),
            'short-copy':source.SELECTED.replace('&payload, 24','&payload, 20'),
            'wrong-destination':source.SELECTED.replace('effect + 0x28','effect + 0x24'),
            'skip-copy':source.SELECTED.replace('if (effect != 0)','if (effect != 0 && payload.sourceByte == 0x42)'),
        }
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            result=self.native(body,'negative-'+label)
            self.assertEqual(result.returncode,23,(label,result.stdout,result.stderr))
        self.receipt['compiled_semantic_negatives']=len(negatives)

    def test_reserved_zeroing_and_saved_S0_restore_are_effective_guest_negatives(self):
        zero=source.SELECTED.replace('    payload.value = 0.0f;',
            '    payload.value = 0.0f;\n    payload.reserved[0] = payload.reserved[1] = payload.reserved[2] = 0;')
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+zero,'zero-reserved')
        self.assertEqual(diagnostic,'')
        raw,_=source.payload(obj);image,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,functions[source.FUNCTION]['value']))
        for phase in (0,8):
            original=self.run_model(self.truth,Case(),phase)
            negative=self.run_model(words,Case(),phase)
            self.assertNotEqual(negative.padding_observed,original.padding_observed)
            self.assertNotEqual(public_memory(negative.memory),public_memory(original.memory))
            wrong=self.truth.copy()
            self.assertEqual(wrong[35],0x8FB00030)
            wrong[35]=0
            with self.assertRaisesRegex(AssertionError,'saved register'):
                self.run_model(wrong,Case(),phase)
        self.receipt['effective_guest_negative_phases']=4

    def test_independent_GNU_code_helper_and_argument_rebases(self):
        count=0
        for i,(code_delta,helper_delta,data_delta) in enumerate(((0x10000,0x20000,0x3000),(0x100000,0x30000,-0x10000),(0x2000000,-0x10000,0x8000))):
            symbols={name:value+helper_delta for name,value in NAMES.items()}
            linked=[]
            for label,obj in (('C',self.obj),('original',self.original)):
                script=self.output/('rebase-%d-%s.ld'%(i,label))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+code_delta))
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                address,text=sections(elf)['.text']
                self.assertEqual(address,source.ENTRY+code_delta)
                linked.append(list(struct.unpack('>39I',text[:156])))
            self.assertEqual(linked[0],linked[1])
            for case in (Case(),Case(255,POINTS[3],mutations=2),Case(allocated=False),Case(destination=1)):
                for phase in (0,8):
                    a=self.run_model(linked[0],case,phase,True,data_delta,symbols,source.ENTRY+code_delta)
                    b=self.run_model(linked[1],case,phase,True,data_delta,symbols,source.ENTRY+code_delta)
                    self.assertEqual(complete(a),complete(b))
                    expected,_=reference(fixture(case,data_delta),case,phase,data_delta)
                    self.assertEqual(public_memory(a.memory,data_delta),public_memory(expected,data_delta))
                    count+=1
        self.receipt.update(independent_GNU_rebase_plans=3,rebased_phases=count)

    def test_actual_owner_typed_caller_Make_and_strict_image_scope(self):
        report=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((report['preserved_neighbors'],report['preserved_raw_caller_functions']),(43,328))
        make=json.loads((self.output/'make-shadow.json').read_text())
        self.assertEqual((make['actual_Make_commands'],make['preserved_padded_caller_functions']),(8,328))
        before=self.values['conker/build/conker.us.elf'];actual=(self.output/'first-linked.elf').read_bytes()
        truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+156]
        source.check_image(before,actual,truth)
        at=source.elf_slot_offset(before,source.ENTRY,156)
        size=next(offset+8 for offset,name,_,_ in source.symbol_rows(before) if name==source.FUNCTION)
        for offset in (0,at-1,at,at+155,at+156,size+3):
            wrong=bytearray(actual);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        for wrong in (actual[:-1],actual+b'\0'):
            with self.assertRaises(ValueError):source.check_image(before,wrong,truth)
        self.receipt.update(preserved_neighbors=43,preserved_caller_functions=328,wrong_image_controls=8)

    def test_live_input_boundaries_no_guards_and_explicit_caller_prototype(self):
        self.assertIn('void func_150F10D4(void *source);',
            source.recovered_caller(self.values[source.CALLER].decode()))
        if self.installed:self.assertTrue(source.audit(ROOT,self.output)['strict_first_link_reproduced'])
        else:
            for name,old in self.values.items():self.assertEqual((ROOT/name).read_bytes(),old,name)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])


if __name__=='__main__':
    unittest.main()
