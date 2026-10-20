"""Unsigned random selection, payload captures and typed caller qualification."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_effect_payload_spawn as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK


ROOT = Path(__file__).resolve().parents[2]
ACTOR, EFFECT, CURRENT = 0x28000, 0x30000, 0x800D154C
NAMES = {'func_150ADA20': source.RANDOM, 'func_15149130': source.SPAWN, 'memcpy': source.COPY}


@dataclass(frozen=True)
class Case:
    number: int = 0
    variant: int = 255
    parameter: int = 0
    byte: int = 0xA7
    allocated: bool = True
    mutations: int = 0
    incoming_alias: int = 0
    padding_alias: bool = False
    destination: int = 0
    wrapper: bool = False
    seed: int = 0xA5


def corpus():
    numbers = (*range(19), 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF, 0x12345678)
    for i, (n, variant, allocated) in enumerate(itertools.product(numbers,
            (0, 1, 255, 256, 0x80000000, 0xFFFFFFFF), (False, True))):
        yield Case(n, variant, (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x12345678)[i % 6],
            i * 73 & 255, allocated, seed=i * 31 & 255)
    for n, allocated, mutations, destination in itertools.product((0, 0xFFFFFFFF), (False, True),
            (1, 2, 3), (0, 1)):
        yield Case(n, 255, 0xABCDEF01, 0x7B, allocated, mutations, destination=destination)
    for alias, phase_seed in itertools.product((1, 2, 3), (0xA5, 0x5A)):
        yield Case(0xFFFFFFFF, 7, 0x12345678, incoming_alias=alias, seed=phase_seed)
    for destination, alias in itertools.product((0, 1, 2, 3), (False, True)):
        yield Case(0x80000000, 255, padding_alias=alias, destination=destination)
    for n, allocated, mutations in itertools.product((0, 0x80000000, 0xFFFFFFFF), (False, True), (0, 3)):
        yield Case(n, 255, 0, allocated=allocated, mutations=mutations, wrapper=True)


def fixture(case, data_delta=0):
    memory = {STACK + i: (i * 17 + case.seed) & 255 for i in range(-0x400, 0x100)}
    for base in (ACTOR + data_delta, EFFECT + data_delta):
        memory.update({base + i: (i * 11 + 0x35) & 255 for i in range(256)})
    put(memory, ACTOR + data_delta + 0x3B, case.byte, 1)
    put(memory, CURRENT, ACTOR + data_delta)
    return memory


def public_event(event, delta=0):
    if event[0] == 'CALL':
        return event[1] != 'ENTER'
    address = event[1]
    return (ACTOR + delta <= address < ACTOR + delta + 256 or
            EFFECT + delta <= address < EFFECT + delta + 256 or CURRENT <= address < CURRENT + 4)


def public_memory(memory, delta=0):
    return {a: v for a, v in memory.items()
            if ACTOR + delta <= a < ACTOR + delta + 256 or EFFECT + delta <= a < EFFECT + delta + 256 or CURRENT <= a < CURRENT + 4}


def destination(case, payload, delta=0):
    return EFFECT + delta + 0x28 if case.destination == 0 else ACTOR + delta + 0x37 if case.destination == 1 else payload + (1 if case.destination == 2 else -1)


def reference(initial, case, phase=0, delta=0):
    memory, events = initial.copy(), []
    entered = STACK + phase - (24 if case.wrapper else 0)
    payload = entered - 72 + 0x3C
    actor = ACTOR + delta
    if case.wrapper:
        events.append(('R', CURRENT, 4, actor))
    events.append(('R', actor + 0x3B, 1, memory[actor + 0x3B]))
    put(memory, payload, actor)
    put(memory, payload + 4, case.byte, 1)
    put(memory, payload + 8, 0)

    def store(address, value, size):
        put(memory, address, value, size)
        events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    events.append(('CALL', 'RANDOM', ()))
    if case.mutations & 1:
        store(actor + 0x3B, 0x5A, 1)
    variant = 3 if case.incoming_alias & 1 else case.variant & 255
    parameter = 0xFEDCBA98 if case.incoming_alias & 2 else case.parameter
    args = (case.number % 9 + 15, 0xFFFFFFFF, 0x52, 0xFFFFFFFF, 1, 0x3F, 12, variant, parameter)
    events.append(('CALL', 'SPAWN', args))
    if case.mutations & 2:
        store(actor + 0x3B, 0xC3, 1)
    if case.padding_alias:
        for i, value in enumerate((0x11, 0x22, 0x33)):
            put(memory, payload + 5 + i, value, 1)
    if case.allocated:
        target = destination(case, payload, delta)
        events.append(('CALL', 'COPY', (target, 'payload', 12)))
        for i in range(12):
            value = memory[payload + i]
            put(memory, target + i, value, 1)
            events.append(('W', target + i, 1, value))
    return memory, [e for e in events if public_event(e, delta)]


class EffectOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0, delta=0, symbols=None,
                 entry=source.ENTRY, connected=None, arguments=None):
        self.case, self.delta = case, delta
        self.by_address = {v: k for k, v in (symbols or NAMES).items()}
        self.main_sp_entry = STACK + phase
        self.padding_observed, self.fired = None, []
        args = (ACTOR + delta, case.variant, case.parameter) if arguments is None else arguments
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=connected)

    def record_call(self, target):
        if target == source.ENTRY:
            self.main_sp_entry = self.r[29]
            self.calls.append(('ENTER', self.arguments(3)))
            self.events.append(('CALL', 'ENTER', self.arguments(3)))
            return
        name = self.by_address[target]
        label = {'func_150ADA20': 'RANDOM', 'func_15149130': 'SPAWN', 'memcpy': 'COPY'}[name]
        args = self.arguments({'RANDOM': 0, 'SPAWN': 9, 'COPY': 3}[label])
        if label == 'COPY':
            self.padding_observed = bytes(self.memory[args[1] + i] for i in range(5, 8))
            args = (args[0], 'payload', args[2])
        self.calls.append((label, args))
        self.events.append(('CALL', label, args))

    def hook(self, target):
        name = self.by_address[target]
        actor = ACTOR + self.delta
        if name == 'func_150ADA20':
            if self.case.mutations & 1:
                self.put(actor + 0x3B, 0x5A, 1)
            if self.case.incoming_alias & 1:
                self.put(self.main_sp_entry + 4, 0x12345603, 4)
                self.fired.append('variant-home')
            if self.case.incoming_alias & 2:
                self.put(self.main_sp_entry + 8, 0xFEDCBA98, 4)
                self.fired.append('parameter-home')
            result = self.case.number
        elif name == 'func_15149130':
            if self.case.mutations & 2:
                self.put(actor + 0x3B, 0xC3, 1)
            if self.case.padding_alias:
                for i, value in enumerate((0x11, 0x22, 0x33)):
                    self.put(self.r[29] + 0x41 + i, value, 1)
                self.fired.append('payload-reserved')
            result = destination(self.case, self.main_sp_entry - 72 + 0x3C, self.delta) - 0x28 if self.case.allocated else 0
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
    rows = ['{0x%Xu,0x%Xu,0x%Xu,%d,%d,%d,%d,%d}' %
            (c.number, c.variant, c.parameter, c.byte, c.allocated, c.mutations, c.destination, c.wrapper) for c in cases]
    return '''typedef unsigned int u32; typedef int s32; typedef unsigned char u8;
typedef signed char s8; typedef short s16; typedef float f32;
''' + source.DECLARATIONS + '''
typedef char payload_size_is_12[sizeof(EffectPayload)==12 ? 1 : -1];
''' + body + '''
typedef struct {u8 bytes[256];} NativeActor;
static NativeActor actor;
static u8 effect[256];
static NativeActor *D_800D154C=&actor;
''' + wrapper + '''
typedef struct {u32 number,variant,parameter;int byte,allocated,mutations,destination,wrapper;} Case;
static const Case cases[]={
''' + ',\n'.join(rows) + '''
};
static const Case *item;
static int stage,error,copies;
static u8 *expected_destination(void) {return item->destination ? actor.bytes+0x37 : effect+0x28;}
static void copy_bytes(void *d,const void *s,u32 n) {
    u8 *dst=d;const u8 *src=s;while(n--)*dst++=*src++;
}
s32 func_150ADA20(void) {
    if(stage++!=0)error=1;
    if(item->mutations&1)actor.bytes[0x3B]=0x5A;
    return (s32)item->number;
}
void *func_15149130(s16 life,s8 a,s8 b,s8 c,u8 flags,u8 kind,s32 size,u8 variant,s32 parameter) {
    if(stage++!=1 || life!=(s16)(item->number%9+15) || a!=-1 || b!=0x52 || c!=-1 ||
       flags!=1 || kind!=0x3F || size!=12 || variant!=(u8)item->variant || (u32)parameter!=item->parameter)error=1;
    if(item->mutations&2)actor.bytes[0x3B]=0xC3;
    return item->allocated ? expected_destination()-0x28 : (void *)0;
}
void *memcpy(void *dst,const void *src,u32 size) {
    const EffectPayload *p=src;
    union {f32 f;u32 u;} value;
    if(stage++!=2 || !item->allocated || dst!=expected_destination() || size!=12) {
        error=1;return dst;
    }
    value.f=p->value;
    if(p->source!=&actor || p->sourceByte!=item->byte || value.u!=0)error=1;
    copy_bytes(dst,src,size);
    copies++;
    return dst;
}
static int test_all(void) {
    u32 c,i;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        EffectPayload decoded;
        item=&cases[c];stage=error=copies=0;
        for(i=0;i<256;i++)actor.bytes[i]=effect[i]=0xA5;
        actor.bytes[0x3B]=(u8)item->byte;
        if(item->wrapper)func_1506F02C(0x12345678);
        else func_150BA4C0(&actor,(u8)item->variant,(s32)item->parameter);
        if(error || stage!=(item->allocated?3:2) || copies!=item->allocated)return 23;
        if(item->allocated) {
            union {f32 f;u32 u;} value;
            copy_bytes(&decoded,expected_destination(),12);
            value.f=decoded.value;
            if(decoded.source!=&actor || decoded.sourceByte!=item->byte || value.u!=0)return 24;
        }
        for(i=0;i<256;i++) {
            int actor_output=item->allocated && item->destination && i>=0x37 && i<0x43;
            int effect_output=item->allocated && !item->destination && i>=0x28 && i<0x34;
            if(!effect_output && effect[i]!=0xA5)return 25;
            if(!actor_output && i!=0x3B && actor.bytes[i]!=0xA5)return 26;
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


class EffectPayloadSpawnTests(unittest.TestCase):
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
        cls.obj, diagnostic = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n' + source.DECLARATIONS + source.SELECTED, 'fresh-selected')
        if diagnostic:
            raise ValueError(diagnostic)
        cls.original = source.original(ROOT, cls.output)
        text, functions = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>39I', text, functions[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>39I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.copy_words = list(struct.unpack_from('>11I', cls.values['conker/conker.us.bin'], 0x22EC0))
        cls.caller_words = list(struct.unpack_from('>12I', cls.values['conker/conker.us.bin'], source.CALLER_ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if not c.incoming_alias and not c.padding_alias and c.destination < 2]
        caller_source = cls.values[source.CALLER].decode()
        lo, hi = source.function_span(caller_source, 'func_1506F02C')
        cls.wrapper = caller_source[lo:hi]
        cls.receipt = dict(cases=len(cls.cases),native_cases=len(cls.native_cases),
            installed=cls.installed,matching_credit=int(cls.installed),compiler_only=True,guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('effect payload qualification:',cls.receipt)

    def run_model(self, words, case, phase=0, connected_copy=False, delta=0, symbols=None, entry=source.ENTRY):
        connected = {}
        if connected_copy:
            at = (symbols or NAMES)['memcpy']
            connected.update(zip(range(at,at+44,4),self.copy_words))
        if case.wrapper:
            connected.update(zip(range(source.ENTRY,source.ENTRY+156,4),words))
            return EffectOracle(self.caller_words,fixture(case,delta),case,phase,delta,symbols,
                source.CALLER_ENTRY,connected,(0x12345678,)).run()
        return EffectOracle(words,fixture(case,delta),case,phase,delta,symbols,entry,connected).run()

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
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),3)
        self.assertEqual(self.words[0],0x27BDFFB8)
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
        self.assertEqual(found,[('func_150265CC',0x150272B0),('func_1506F02C',0x1506F044)])
        dispatcher=struct.unpack_from('>10I',rom,0x54748)
        self.assertEqual(dispatcher,(0x8FA40764,0x93A50773,0x14800003,0,
            0x10000A3E,0x24020001,opcode,0x24060001,0x10000A3A,0x24020001))
        self.assertEqual(self.caller_words[0],0x27BDFFE8)
        self.assertEqual(self.caller_words[8:], [0x8FBF0014,0x27BD0018,0x03E00008,0])
        self.receipt['all_direct_retail_call_sites']=found
        self.receipt['dispatcher_ABI_static_window_only']=True

    def test_full_model_reference_order_captures_reserved_bytes_and_retail_memcpy(self):
        visits=set();phases=0;fired=set();connected=0;configured=0;wrappers=0
        for case in self.cases:
            for phase in (0,8):
                expected,events=reference(fixture(case),case,phase)
                for copy in (False,True):
                    a=self.run_model(self.truth,case,phase,copy)
                    b=self.run_model(self.words,case,phase,copy)
                    self.assertEqual(complete(a),complete(b))
                    self.assertEqual(public_memory(b.memory),public_memory(expected),case)
                    observed=[event for event in b.events if public_event(event)]
                    self.assertEqual(observed,events,(case,copy))
                    if case.allocated:
                        payload=b.main_sp_entry-72+0x3C
                        wanted=bytes((0x11,0x22,0x33)) if case.padding_alias else bytes(fixture(case)[payload+i] for i in range(5,8))
                        self.assertEqual(b.padding_observed,wanted)
                    fired.update(b.fired);visits.update(b.visits);phases+=1
                    configured+=copy
                    entered_copy=source.COPY in b.visits
                    self.assertEqual(entered_copy,bool(copy and case.allocated))
                    connected+=entered_copy
                    if case.wrapper:
                        self.assertIn(source.CALLER_ENTRY,b.visits)
                        self.assertIn(source.ENTRY,b.visits)
                        wrappers+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=visits)
        self.assertEqual(fired,{'variant-home','parameter-home','payload-reserved'})
        self.receipt.update(model_variant_phases=phases,complete_final_states=phases,
            connected_original_memcpy_phases=connected,retail_target_words_visited=39,
            configured_memcpy_phases=configured,original_C_wrapper_phases=wrappers,
            fired_physical_alias_kinds=sorted(fired),hardware_FCSR_modeled=False)

    def test_native32_three_optimizations_valid_caller_and_defined_payload_fields(self):
        for optimization in ('-O0','-O2','-O3'):
            result=self.native(source.SELECTED,'native',optimization)
            self.assertEqual(result.returncode,0,(optimization,result.stdout,result.stderr))
        self.receipt.update(native_optimizations=3,trap_UBSan=True,
            native_reserved_bytes_unconstrained=True)

    def test_compiled_semantic_unsigned_capture_flags_size_destination_and_copy_negatives(self):
        assignment='    payload.sourceByte = ((u8 *)source)[0x3B];\n'
        late=source.SELECTED.replace(assignment,'').replace('    if (effect != 0) {',assignment+'    if (effect != 0) {')
        negatives={
            'signed-modulus':source.SELECTED.replace('(u32)func_150ADA20()','func_150ADA20()'),
            'late-capture':late,
            'wrong-flags':source.SELECTED.replace('1, 0x3F, 0xC','0, 0x3F, 0xC'),
            'short-copy':source.SELECTED.replace('&payload, 12','&payload, 8'),
            'wrong-destination':source.SELECTED.replace('effect + 0x28','effect + 0x24'),
            'skip-copy':source.SELECTED.replace('if (effect != 0)','if (effect != 0 && parameter == 123)'),
        }
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            result=self.native(body,'negative-'+label)
            self.assertEqual(result.returncode,23,(label,result.stdout,result.stderr))
        self.receipt['compiled_semantic_negatives']=len(negatives)

    def test_reserved_zeroing_and_early_variant_capture_are_effective_guest_negatives(self):
        zero=source.SELECTED.replace('    payload.value = 0.0f;',
            '    payload.value = 0.0f;\n    payload.reserved[0] = payload.reserved[1] = payload.reserved[2] = 0;')
        cached=source.SELECTED.replace('    EffectPayload payload;',
            '    EffectPayload payload;\n    volatile u8 capturedVariant = variant;').replace('0xC, variant, parameter','0xC, capturedVariant, parameter')
        for label,body,case in (('zero-reserved',zero,Case()),('cached-variant',cached,Case(variant=7,incoming_alias=1))):
            obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+body,label)
            self.assertEqual(diagnostic,'')
            raw,_=source.payload(obj);image,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
            words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,functions[source.FUNCTION]['value']))
            for phase in (0,8):
                original=self.run_model(self.truth,case,phase)
                negative=self.run_model(words,case,phase)
                if label=='zero-reserved':
                    self.assertNotEqual(negative.padding_observed,original.padding_observed)
                    self.assertNotEqual(public_memory(negative.memory),public_memory(original.memory))
                else:
                    self.assertIn('variant-home',negative.fired)
                    self.assertNotEqual(negative.calls,original.calls)
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
            for case in (Case(),Case(0xFFFFFFFF,0xABCDEF01,0x80000000,mutations=3),Case(allocated=False),Case(destination=1)):
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
        self.assertEqual((report['preserved_neighbors'],report['preserved_raw_caller_functions']),(5,328))
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
        self.receipt.update(preserved_neighbors=5,preserved_caller_functions=328,wrong_image_controls=8)

    def test_live_input_boundaries_no_guards_and_explicit_caller_prototype(self):
        self.assertIn('void func_150BA4C0(void *source, u8 variant, s32 parameter);',
            source.recovered_caller(self.values[source.CALLER].decode()))
        if self.installed:self.assertTrue(source.audit(ROOT,self.output)['strict_first_link_reproduced'])
        else:
            for name,old in self.values.items():self.assertEqual((ROOT/name).read_bytes(),old,name)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])


if __name__=='__main__':
    unittest.main()
