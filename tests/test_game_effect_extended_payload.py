"""Extended payload layout, global capture and original factory-wrapper contract."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_effect_extended_payload as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
ACTOR, EFFECT = 0x28000, 0x30000
NAMES = {'func_151491F4': source.FACTORY, 'func_15149130': source.SPAWN,
         'memcpy': source.COPY, 'D_800A8D64': source.CONSTANT}
VALUES = (0, 0x80000000, 0x3F800000, 0xBFA00000, 0x7F7FFFFF, 0x00800000,
          0x7F800000, 0x7FC12345, 0x7FA12345)


@dataclass(frozen=True)
class Case:
    byte: int = 0xA7
    variant: int = 255
    value: int = 0x3F800000
    allocated: bool = True
    mutate: bool = False
    padding_alias: bool = False
    home_alias: bool = False
    destination: int = 0
    seed: int = 0xA5


def corpus():
    for i, (byte, variant, allocated, mutate) in enumerate(itertools.product(
            (0, 127, 128, 255), (0, 1, 255, 256, 0x80000000, 0xFFFFFFFF), (False, True), (False, True))):
        yield Case(byte, variant, VALUES[i % len(VALUES)], allocated, mutate, seed=i * 31 & 255)
    for value, allocated, mutate in itertools.product(VALUES, (False, True), (False, True)):
        yield Case(0x7B, 0xFFFFFFFF, value, allocated, mutate)
    for destination, padding, home, seed in itertools.product(range(4), (False, True), (False, True), (0xA5, 0x5A)):
        yield Case(255, 255, 0xBFA00000, mutate=True, destination=destination,
                   padding_alias=padding, home_alias=home, seed=seed)


def fixture(case, delta=0, constant=source.CONSTANT):
    memory = {STACK + i: (i * 17 + case.seed) & 255 for i in range(-0x400, 0x100)}
    for base in (ACTOR + delta, EFFECT + delta):
        memory.update({base + i: (i * 11 + 0x35) & 255 for i in range(256)})
    put(memory, ACTOR + delta + 0x3B, case.byte, 1)
    put(memory, constant, case.value)
    return memory


def public_event(event, delta=0, constant=source.CONSTANT):
    if event[0] == 'CALL':
        return True
    return (constant <= event[1] < constant + 4 or
            any(base <= event[1] < base + 256 for base in (ACTOR + delta, EFFECT + delta)))


def public_memory(memory, delta=0, constant=source.CONSTANT):
    return {a: v for a, v in memory.items()
            if constant <= a < constant + 4 or any(base <= a < base + 256 for base in (ACTOR + delta, EFFECT + delta))}


def destination(case, payload, delta=0):
    return (EFFECT + delta + 0x28 if case.destination == 0 else ACTOR + delta + 0x37
            if case.destination == 1 else payload + (1 if case.destination == 2 else -1))


def reference(initial, case, phase=0, delta=0, constant=source.CONSTANT, factory=False):
    memory, events = initial.copy(), []
    payload, actor = STACK + phase - 80 + 0x2C, ACTOR + delta
    events.append(('R', constant, 4, read(memory, constant)))
    events.append(('R', actor + 0x3B, 1, memory[actor + 0x3B]))
    put(memory, payload, actor)
    put(memory, payload + 4, memory[actor + 0x3B], 1)
    put(memory, payload + 8, read(memory, constant))
    for offset in (12, 20, 24, 28):
        put(memory, payload + offset, 0)
    put(memory, payload + 16, 1, 1)
    events.append(('CALL', 'FACTORY', (300, 0xFFFFFFFF, 5, 0, 1, 32, case.variant & 255, 0)))
    if factory:
        events.append(('CALL', 'SPAWN', (300, 0xFFFFFFFF, 5, 0xFFFFFFFF, 0, 1, 32, case.variant & 255, 0)))
    if case.mutate:
        for at, value, size in ((actor + 0x3B, 0xC3, 1), (constant, 0x41000000, 4)):
            put(memory, at, value, size)
            events.append(('W', at, size, value))
    if case.padding_alias:
        for offset, value in zip((5, 6, 7, 17, 18, 19), (0x11, 0x22, 0x33, 0x44, 0x55, 0x66)):
            put(memory, payload + offset, value, 1)
    if case.allocated:
        target = destination(case, payload, delta)
        events.append(('CALL', 'COPY', (target, 'payload', 32)))
        for i in range(32):
            value = memory[payload + i]
            put(memory, target + i, value, 1)
            events.append(('W', target + i, 1, value))
    return memory, [e for e in events if public_event(e, delta, constant)]


class ExtendedOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0, delta=0, symbols=None,
                 entry=source.ENTRY, connected=None):
        self.case, self.delta = case, delta
        self.names = symbols or NAMES
        self.by_address = {v: k for k, v in self.names.items()}
        self.main_sp_entry = STACK + phase
        self.padding_observed, self.snapshot, self.fired = None, None, []
        super().__init__(words, memory, phase=phase, entry=entry,
                         arguments=(ACTOR + delta, case.variant), connected=connected)

    def record_call(self, target):
        label = {'func_151491F4': 'FACTORY', 'func_15149130': 'SPAWN', 'memcpy': 'COPY'}[self.by_address[target]]
        args = self.arguments({'FACTORY': 8, 'SPAWN': 9, 'COPY': 3}[label])
        if label == 'FACTORY':
            at = self.main_sp_entry - 80 + 0x2C
            self.snapshot = bytes(self.memory[at + i] for i in range(32))
        if label == 'COPY':
            self.padding_observed = bytes(self.memory[args[1] + i] for i in (5, 6, 7, 17, 18, 19))
            args = (args[0], 'payload', args[2])
        self.calls.append((label, args))
        self.events.append(('CALL', label, args))

    def hook(self, target):
        name = self.by_address[target]
        if name in ('func_151491F4', 'func_15149130'):
            payload = self.main_sp_entry - 80 + 0x2C
            if self.case.mutate:
                self.put(ACTOR + self.delta + 0x3B, 0xC3, 1)
                self.put(self.names['D_800A8D64'], 0x41000000, 4)
            if self.case.padding_alias:
                for at, value in zip((5, 6, 7, 17, 18, 19), (0x11, 0x22, 0x33, 0x44, 0x55, 0x66)):
                    self.put(payload + at, value, 1)
                self.fired.append('both-reserved-ranges')
            if self.case.home_alias:
                self.put(self.main_sp_entry, 0xFEDCBA98, 4)
                self.put(self.main_sp_entry + 4, 0x12345603, 4)
                self.fired.append('source-and-variant-homes')
            result = destination(self.case, payload, self.delta) - 0x28 if self.case.allocated else 0
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


def native_harness(body, cases):
    rows = ['{%d,0x%Xu,0x%Xu,%d,%d,%d}' %
            (c.byte, c.variant, c.value, c.allocated, c.mutate, c.destination) for c in cases]
    return '''typedef unsigned int u32; typedef int s32; typedef unsigned char u8;
typedef signed char s8; typedef short s16; typedef float f32;
''' + source.DECLARATIONS + '''
typedef char payload_size_is_32[sizeof(ExtendedEffectPayload)==32 ? 1 : -1];
''' + body + '''
static u8 actor[256],effect[256];
f32 D_800A8D64;
typedef struct {int byte;u32 variant,value;int allocated,mutate,destination;} Case;
static const Case cases[]={
''' + ',\n'.join(rows) + '''
};
static const Case *item;
static int stage,error,copies;
static u32 word(f32 f) {union {f32 f;u32 u;} v;v.f=f;return v.u;}
static f32 real(u32 u) {union {f32 f;u32 u;} v;v.u=u;return v.f;}
static u8 *expected_destination(void) {return item->destination ? actor+0x37 : effect+0x28;}
static void copy_bytes(void *d,const void *s,u32 n) {
    u8 *dst=d;const u8 *src=s;while(n--)*dst++=*src++;
}
void *func_151491F4(s16 life,s8 a,s8 b,u8 flags,u8 kind,s32 size,u8 variant,s32 parameter) {
    if(stage++!=0 || life!=300 || a!=-1 || b!=5 || flags!=0 || kind!=1 ||
       size!=32 || variant!=(u8)item->variant || parameter!=0)error=1;
    if(item->mutate) {actor[0x3B]=0xC3;D_800A8D64=8.0f;}
    return item->allocated ? expected_destination()-0x28 : (void *)0;
}
void *memcpy(void *dst,const void *src,u32 size) {
    const ExtendedEffectPayload *p=src;int i;
    if(stage++!=1 || !item->allocated || dst!=expected_destination() || size!=32) {
        error=1;return dst;
    }
    if(p->source!=actor || p->sourceByte!=item->byte || word(p->value)!=item->value ||
       word(p->zero)!=0 || p->active!=1)error=1;
    for(i=0;i<3;i++)if(word(p->vector[i])!=0)error=1;
    copy_bytes(dst,src,size);copies++;
    return dst;
}
static int test_all(void) {
    u32 c,i;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        ExtendedEffectPayload decoded;
        item=&cases[c];stage=error=copies=0;
        for(i=0;i<256;i++)actor[i]=effect[i]=0xA5;
        actor[0x3B]=(u8)item->byte;D_800A8D64=real(item->value);
        func_151A499C(actor,(u8)item->variant);
        if(error || stage!=(item->allocated?2:1) || copies!=item->allocated)return 23;
        if(word(D_800A8D64)!=(item->mutate?0x41000000u:item->value))return 24;
        if(item->allocated) {
            copy_bytes(&decoded,expected_destination(),32);
            if(decoded.source!=actor || decoded.sourceByte!=item->byte || word(decoded.value)!=item->value ||
               word(decoded.zero)!=0 || decoded.active!=1)return 24;
            for(i=0;i<3;i++)if(word(decoded.vector[i])!=0)return 24;
        }
        for(i=0;i<256;i++) {
            int ao=item->allocated && item->destination && i>=0x37 && i<0x57;
            int eo=item->allocated && !item->destination && i>=0x28 && i<0x48;
            if(!eo && effect[i]!=0xA5)return 25;
            if(!ao && i!=0x3B && actor[i]!=0xA5)return 26;
        }
        if(actor[0x3B]!=(item->allocated && item->destination ? item->byte :
                       item->mutate ? 0xC3 : item->byte))return 27;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=test_all();
    __asm__ volatile("int $0x80" : : "a"(1),"b"(status) : "memory");
    __builtin_unreachable();
}
'''


class EffectExtendedPayloadTests(unittest.TestCase):
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
        cls.factory_words = list(struct.unpack_from('>28I', cls.values['conker/conker.us.bin'], source.FACTORY_ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if not c.padding_alias and not c.home_alias and c.destination < 2
                            and c.value & 0x7F800000 != 0x7F800000]
        cls.receipt = dict(cases=len(cls.cases),native_cases=len(cls.native_cases),
            installed=cls.installed,matching_credit=int(cls.installed),compiler_only=True,guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('extended effect qualification:',cls.receipt)

    def run_model(self, words, case, phase=0, copy=False, factory=False, delta=0, symbols=None, entry=source.ENTRY):
        connected = {}
        symbols = symbols or NAMES
        if copy:
            at = symbols['memcpy']
            connected.update(zip(range(at,at+44,4),self.copy_words))
        if factory:
            self.assertEqual(symbols,NAMES)
            connected.update(zip(range(source.FACTORY,source.FACTORY+112,4),self.factory_words))
        return ExtendedOracle(words,fixture(case,delta,symbols['D_800A8D64']),case,phase,delta,symbols,entry,connected).run()

    def native(self, body, label, optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+optimization)
        command=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
            str(unit),'-o',str(binary)]
        process=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        return subprocess.run([str(binary)],capture_output=True,timeout=30)

    def test_direct_complete_bindings_pristine_caller_and_existing_factory(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(self.original))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),4)
        self.assertEqual(self.words[0],0x27BDFFB0)
        self.assertEqual(self.words[8],0xAFAE002C)
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000 | (source.ENTRY>>2 & 0x3FFFFFF)
        found=[];rom=self.values['conker/conker.us.bin']
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:continue
            vram,start=DEFAULT_SEGMENTS['us'][row['section']]
            entry=function_vram(row,symbols);offset=entry-vram+start
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],rom,offset)
            found.extend((row['function'],entry+i*4) for i,w in enumerate(words) if w==opcode)
        self.assertEqual(found,[('func_151A3390',0x151A3458)])
        self.assertEqual(struct.unpack_from('>5I',rom,0x1D0904),
                         (0x02002025,opcode,0x93A5009F,0x24180FA0,0xAFB80010))
        for entry,offset,size in ((source.FACTORY,source.FACTORY_ROM,112),(source.COPY,0x22EC0,44)):
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,size)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+size],rom[offset:offset+size])
        self.receipt.update(all_direct_retail_call_sites=found,caller_ABI_static_window_only=True,
                            factory_wrapper_original_words=28)

    def test_full_states_reference_both_reserved_ranges_and_fired_original_helpers(self):
        visits=set();phases=0;fired=set();copies=0;configured=0;factories=0
        for case in self.cases:
            for phase,copy,factory in itertools.product((0,8),(False,True),(False,True)):
                expected,events=reference(fixture(case),case,phase,factory=factory)
                a=self.run_model(self.truth,case,phase,copy,factory)
                b=self.run_model(self.words,case,phase,copy,factory)
                self.assertEqual(complete(a),complete(b))
                self.assertEqual(public_memory(b.memory),public_memory(expected),case)
                self.assertEqual([e for e in b.events if public_event(e)],events,(case,copy,factory))
                self.assertEqual(struct.unpack_from('>I',b.snapshot)[0],ACTOR)
                self.assertEqual(b.snapshot[4],case.byte)
                self.assertEqual(struct.unpack_from('>2I',b.snapshot,8),(case.value,0))
                self.assertEqual(b.snapshot[16],1)
                self.assertEqual(struct.unpack_from('>3I',b.snapshot,20),(0,0,0))
                if case.allocated:
                    at=STACK+phase-80+0x2C
                    wanted=bytes((0x11,0x22,0x33,0x44,0x55,0x66)) if case.padding_alias else bytes(
                        fixture(case)[at+i] for i in (5,6,7,17,18,19))
                    self.assertEqual(b.padding_observed,wanted)
                self.assertEqual(source.COPY in b.visits,bool(copy and case.allocated))
                self.assertEqual(source.FACTORY in b.visits,factory)
                copies+=source.COPY in b.visits;configured+=copy;factories+=factory
                visits.update(b.visits);fired.update(b.fired);phases+=1
        for entry,size in ((source.ENTRY,156),(source.FACTORY,112),(source.COPY,44)):
            self.assertTrue(set(range(entry,entry+size,4))<=visits)
        self.assertEqual(fired,{'both-reserved-ranges','source-and-variant-homes'})
        self.receipt.update(complete_final_states=phases,model_variant_phases=phases,
            configured_memcpy_phases=configured,connected_original_memcpy_phases=copies,
            original_factory_wrapper_phases=factories,all_39_target_28_factory_11_copy_words_visited=True,
            fired_physical_alias_kinds=sorted(fired),nonfinite_patterns_guest_only=True,hardware_FCSR_modeled=False)

    def test_native32_three_optimizations_defined_fields_fences_and_factory_mutations(self):
        for optimization in ('-O0','-O2','-O3'):
            result=self.native(source.SELECTED,'native',optimization)
            self.assertEqual(result.returncode,0,(optimization,result.stdout,result.stderr))
        self.receipt.update(native_optimizations=3,trap_UBSan=True,native_reserved_bytes_unconstrained=True)

    def test_compiled_semantic_capture_active_zero_variant_size_destination_and_copy_negatives(self):
        byte='    payload.sourceByte = actor[0x3B];\n'
        value='    payload.value = D_800A8D64;\n'
        def late(assignment):
            return source.SELECTED.replace(assignment,'').replace('    if (effect != 0) {',assignment+'    if (effect != 0) {')
        negatives={
            'late-byte':late(byte),'late-global':late(value),
            'wrong-active':source.SELECTED.replace('payload.active = 1','payload.active = 0'),
            'wrong-zero':source.SELECTED.replace('payload.zero = 0.0f','payload.zero = 1.0f'),
            'wrong-variant':source.SELECTED.replace('32, variant, 0','32, variant ^ 0x80, 0'),
            'wrong-size':source.SELECTED.replace('1, 32, variant','1, 16, variant'),
            'short-copy':source.SELECTED.replace('&payload, 32','&payload, 28'),
            'wrong-destination':source.SELECTED.replace('effect + 0x28','effect + 0x24'),
            'skip-copy':source.SELECTED.replace('if (effect != 0)','if (effect != 0 && payload.active == 2)'),
        }
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            result=self.native(body,'negative-'+label)
            self.assertEqual(result.returncode,23,(label,result.stdout,result.stderr))
        self.receipt['compiled_semantic_negatives']=len(negatives)

    def test_reserved_zeroing_and_rejected_layout_have_effective_evidence(self):
        zero=source.SELECTED.replace('    payload.zero = 0.0f;',
            '    payload.zero = 0.0f;\n    payload.reserved0[0] = payload.reserved0[1] = payload.reserved0[2] = 0;\n'
            '    payload.reserved1[0] = payload.reserved1[1] = payload.reserved1[2] = 0;')
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+zero,'zero-reserved')
        self.assertEqual(diagnostic,'')
        raw,_=source.payload(obj);image,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,functions[source.FUNCTION]['value']))
        for phase in (0,8):
            original=self.run_model(self.truth,Case(),phase)
            negative=self.run_model(words,Case(),phase)
            self.assertNotEqual(negative.padding_observed,original.padding_observed)
            self.assertNotEqual(public_memory(negative.memory),public_memory(original.memory))
        wrong=source.SELECTED.replace('    u8 *effect;\n    ExtendedEffectPayload payload;',
                                      '    ExtendedEffectPayload payload;\n    u8 *effect;')
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+wrong,'rejected-layout')
        self.assertEqual(diagnostic,'')
        image,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        candidate=struct.unpack_from('>39I',image,functions[source.FUNCTION]['value'])
        self.assertEqual(sum(a!=b for a,b in zip(candidate,self.truth)),9)
        self.receipt.update(effective_reserved_negative_phases=2,rejected_layout_word_differences=9)

    def test_independent_GNU_code_helpers_global_HI_LO_carries_and_argument_rebases(self):
        count=0
        for i,(code_delta,helper_delta,data_delta,constant) in enumerate((
                (0x10000,0x20000,0x3000,0x800B7FFC),
                (0x100000,0x30000,-0x10000,0x800B8000),
                (0x2000000,-0x10000,0x8000,0x800AFFFC))):
            symbols={name:(constant if name=='D_800A8D64' else value+helper_delta) for name,value in NAMES.items()}
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
            for case in (Case(),Case(255,0xFFFFFFFF,0x7FC12345,mutate=True),Case(allocated=False),Case(destination=1)):
                for phase in (0,8):
                    a=self.run_model(linked[0],case,phase,True,False,data_delta,symbols,source.ENTRY+code_delta)
                    b=self.run_model(linked[1],case,phase,True,False,data_delta,symbols,source.ENTRY+code_delta)
                    self.assertEqual(complete(a),complete(b))
                    expected,_=reference(fixture(case,data_delta,constant),case,phase,data_delta,constant)
                    self.assertEqual(public_memory(a.memory,data_delta,constant),public_memory(expected,data_delta,constant))
                    count+=1
        self.receipt.update(independent_GNU_rebase_plans=3,rebased_phases=count,global_HI_LO_signed_carries=True)

    def test_actual_full_owner_Make_and_strict_first_image_scope(self):
        report=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((report['preserved_neighbors'],report['relocations']),(22,4))
        make=json.loads((self.output/'make-shadow.json').read_text())
        self.assertEqual(make['actual_Make_commands'],5)
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
        names={'D_800A8D64','D_800A80E4','D_80096914'}
        for offset,name,_,string in source.symbol_rows(actual):
            if name not in names:continue
            for at in (offset+7,string+2):
                wrong=bytearray(actual);wrong[at]^=1
                with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        canonical=lambda image:sorted((name,fields[1:]) for _,name,fields,_ in source.symbol_rows(image)
                                      if name!=source.FUNCTION)
        self.assertEqual(canonical(before),canonical(actual))
        self.receipt.update(preserved_neighbors=22,wrong_image_controls=14,closed_metadata_symbol_cycle=3)

    def test_live_inputs_frozen_history_and_no_new_guards(self):
        if self.installed:
            self.assertTrue(source.audit(ROOT,self.output)['strict_first_link_reproduced'])
        else:
            for name,old in self.values.items():self.assertEqual((ROOT/name).read_bytes(),old,name)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])


if __name__=='__main__':
    unittest.main()
