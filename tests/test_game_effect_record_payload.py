"""Record captures, allocation-result lifetime, copied padding and typed caller."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_effect_record_payload as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
RECORD, EFFECT = 0x12028000, 0x30000
NAMES = {'func_15149130': source.SPAWN, 'memcpy': source.COPY}
WORDS = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x89ABCDEF)
SELECTORS = (0, 255, 128, 0xFFFFFF80, 0x12345678, 0x80000001)


@dataclass(frozen=True)
class Case:
    value: int = 0x89ABCDEF
    selector: int = 0x12345678
    variant: int = 255
    parameter: int = 0
    allocated: bool = True
    mutate: bool = False
    padding_alias: bool = False
    home_alias: bool = False
    destination: int = 0
    wrapper: bool = False
    seed: int = 0xA5


def corpus():
    variants = (0, 1, 255, 256, 0x80000000, 0xFFFFFFFF)
    for i, (value, selector, allocated, mutate) in enumerate(itertools.product(
            WORDS, SELECTORS, (False, True), (False, True))):
        yield Case(value, selector, variants[i // 4 % 6], WORDS[i // 3 % 6],
                   allocated, mutate, seed=i * 31 & 255)
    for parameter, allocated, mutate in itertools.product(WORDS, (False, True), (False, True)):
        yield Case(0x80000000, 0xFFFFFF80, 0xFFFFFFFF, parameter, allocated, mutate)
    for destination, padding, home, seed in itertools.product(range(5), (False, True), (False, True), (0xA5, 0x5A)):
        yield Case(mutate=True, destination=destination, padding_alias=padding, home_alias=home, seed=seed)
    for value, allocated, mutate in itertools.product((0, 0xFFFFFFFF), (False, True), (False, True)):
        yield Case(value, 0x80000001, 255, 1, allocated, mutate, wrapper=True)


def fixture(case, delta=0):
    memory = {STACK + i: (i * 17 + case.seed) & 255 for i in range(-0x400, 0x100)}
    for base in (RECORD + delta, EFFECT + delta):
        memory.update({base + i: (i * 11 + 0x35) & 255 for i in range(256)})
    put(memory, RECORD + delta + 0x18, case.value)
    put(memory, RECORD + delta + 0x1C, case.selector)
    return memory


def public_event(event, delta=0):
    if event[0] == 'CALL':
        return event[1] != 'ENTER'
    return any(base <= event[1] < base + 256 for base in (RECORD + delta, EFFECT + delta))


def public_memory(memory, delta=0):
    return {a: v for a, v in memory.items()
            if any(base <= a < base + 256 for base in (RECORD + delta, EFFECT + delta))}


def destination(case, payload, delta=0):
    return (EFFECT + delta + 0x28 if case.destination == 0 else RECORD + delta + 0x37
            if case.destination == 1 else RECORD + delta + 0x17 if case.destination == 4
            else payload + (1 if case.destination == 2 else -1))


def reference(initial, case, phase=0, delta=0):
    memory, events = initial.copy(), []
    entry = STACK + phase - (24 if case.wrapper else 0)
    payload, record = entry - 72 + 0x34, RECORD + delta
    variant, parameter = (255, 1) if case.wrapper else (case.variant & 255, case.parameter)
    put(memory, payload, record)
    for offset, value in ((0x18, case.value), (0x1C, case.selector)):
        events.append(('R', record + offset, 4, value))
    put(memory, payload + 4, case.value)
    put(memory, payload + 8, 0)
    put(memory, payload + 12, case.selector & 255, 1)
    events.append(('CALL', 'SPAWN', (300, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0, 30, 16, variant, parameter)))
    if case.mutate:
        for offset, value in ((0x18, 0x2468ACE0), (0x1C, 0x7F008000)):
            put(memory, record + offset, value)
            events.append(('W', record + offset, 4, value))
    if case.padding_alias:
        for i, value in enumerate((0x11, 0x22, 0x33)):
            put(memory, payload + 13 + i, value, 1)
    result = 0
    if case.allocated:
        target = destination(case, payload, delta)
        result = target - 0x28
        put(memory, payload + 16, result)
        events.append(('CALL', 'COPY', (target, 'payload', 16)))
        for i in range(16):
            value = memory[payload + i]
            put(memory, target + i, value, 1)
            events.append(('W', target + i, 1, value))
        # A physical +1 copy can reach the real saved-result home after the payload.
        result = read(memory, payload + 16)
    return memory, [e for e in events if public_event(e, delta)], 1 if case.wrapper else result


class RecordOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0, delta=0, symbols=None,
                 entry=source.ENTRY, connected=None, arguments=None):
        self.case, self.delta = case, delta
        self.by_address = {v: k for k, v in (symbols or NAMES).items()}
        self.main_sp_entry = STACK + phase
        self.padding_observed, self.snapshot, self.fired = None, None, []
        args = (RECORD + delta, case.variant, case.parameter) if arguments is None else arguments
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=connected)

    def record_call(self, target):
        if target == source.ENTRY:
            self.main_sp_entry = self.r[29]
            self.calls.append(('ENTER', self.arguments(3)))
            self.events.append(('CALL', 'ENTER', self.arguments(3)))
            return
        label = {'func_15149130': 'SPAWN', 'memcpy': 'COPY'}[self.by_address[target]]
        args = self.arguments({'SPAWN': 9, 'COPY': 3}[label])
        if label == 'SPAWN':
            at = self.main_sp_entry - 72 + 0x34
            self.snapshot = bytes(self.memory[at + i] for i in range(16))
        if label == 'COPY':
            self.padding_observed = bytes(self.memory[args[1] + i] for i in range(13, 16))
            args = (args[0], 'payload', args[2])
        self.calls.append((label, args))
        self.events.append(('CALL', label, args))

    def hook(self, target):
        if self.by_address[target] == 'func_15149130':
            payload = self.main_sp_entry - 72 + 0x34
            if self.case.mutate:
                self.put(RECORD + self.delta + 0x18, 0x2468ACE0, 4)
                self.put(RECORD + self.delta + 0x1C, 0x7F008000, 4)
            if self.case.padding_alias:
                for i, value in enumerate((0x11, 0x22, 0x33)):
                    self.put(payload + 13 + i, value, 1)
                self.fired.append('payload-reserved')
            if self.case.home_alias:
                for i, value in enumerate((0xFEDCBA98, 0x12345603, 0x2468ACE0)):
                    self.put(self.main_sp_entry + i * 4, value, 4)
                self.fired.append('all-incoming-homes')
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


def native_harness(body, cases, wrapper):
    rows = ['{0x%Xu,0x%Xu,0x%Xu,0x%Xu,%d,%d,%d,%d}' %
            (c.value, c.selector, c.variant, c.parameter, c.allocated, c.mutate, c.destination, c.wrapper) for c in cases]
    return '''typedef unsigned int u32; typedef int s32; typedef unsigned char u8;
typedef signed char s8; typedef short s16; typedef float f32;
''' + source.DECLARATIONS + '''
typedef char payload_size_is_16[sizeof(EffectRecordPayload)==16 ? 1 : -1];
''' + body + '\n' + wrapper + '''
typedef struct {u8 prefix[24];s32 value,selector;u8 suffix[224];} NativeRecord;
static NativeRecord record;
static u8 effect[256];
typedef struct {u32 value,selector,variant,parameter;int allocated,mutate,destination,wrapper;} Case;
static const Case cases[]={
''' + ',\n'.join(rows) + '''
};
static const Case *item;
static int stage,error,copies;
static u8 *expected_destination(void) {return item->destination ? (u8 *)&record+0x37 : effect+0x28;}
static void copy_bytes(void *d,const void *s,u32 n) {
    u8 *dst=d;const u8 *src=s;while(n--)*dst++=*src++;
}
void *func_15149130(s16 life,s8 a,s8 b,s8 c,u8 flags,u8 kind,s32 size,u8 variant,s32 parameter) {
    u8 wantedVariant=item->wrapper ? 255 : (u8)item->variant;
    u32 wantedParameter=item->wrapper ? 1 : item->parameter;
    if(stage++!=0 || life!=300 || a!=-1 || b!=-1 || c!=-1 || flags!=0 || kind!=30 ||
       size!=16 || variant!=wantedVariant || (u32)parameter!=wantedParameter)error=1;
    if(item->mutate) {record.value=0x2468ACE0;record.selector=0x7F008000;}
    return item->allocated ? expected_destination()-0x28 : (void *)0;
}
void *memcpy(void *dst,const void *src,u32 size) {
    const EffectRecordPayload *p=src;
    if(stage++!=1 || !item->allocated || dst!=expected_destination() || size!=16) {
        error=1;return dst;
    }
    if(p->source!=&record || (u32)p->value!=item->value || p->zero!=0 ||
       p->selector!=(u8)item->selector)error=1;
    copy_bytes(dst,src,size);copies++;
    return dst;
}
static int test_all(void) {
    u32 c,i;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        EffectRecordPayload decoded;void *result=0;
        item=&cases[c];stage=error=copies=0;
        for(i=0;i<256;i++)((u8 *)&record)[i]=effect[i]=0xA5;
        record.value=(s32)item->value;record.selector=(s32)item->selector;
        if(item->wrapper) {
            if(func_15013F9C(&record)!=1)return 23;
        } else result=func_151CD2C0(&record,(u8)item->variant,(s32)item->parameter);
        if(error || stage!=(item->allocated?2:1) || copies!=item->allocated)return 23;
        if(!item->wrapper && result!=(item->allocated ? expected_destination()-0x28 : (void *)0))return 23;
        if((u32)record.value!=(item->mutate?0x2468ACE0u:item->value) ||
           (u32)record.selector!=(item->mutate?0x7F008000u:item->selector))return 24;
        if(item->allocated) {
            copy_bytes(&decoded,expected_destination(),16);
            if(decoded.source!=&record || (u32)decoded.value!=item->value || decoded.zero!=0 ||
               decoded.selector!=(u8)item->selector)return 24;
        }
        for(i=0;i<256;i++) {
            int ro=item->allocated && item->destination && i>=0x37 && i<0x47;
            int eo=item->allocated && !item->destination && i>=0x28 && i<0x38;
            if(!eo && effect[i]!=0xA5)return 25;
            if(!ro && !(i>=0x18 && i<0x20) && ((u8 *)&record)[i]!=0xA5)return 26;
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


class EffectRecordPayloadTests(unittest.TestCase):
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
        cls.caller_words = list(struct.unpack_from('>10I', cls.values['conker/conker.us.bin'], source.CALLER_ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if not c.padding_alias and not c.home_alias and c.destination < 2]
        caller=source.recovered_caller(cls.values[source.CALLER].decode())
        lo,hi=source.function_span(caller,'func_15013F9C')
        cls.wrapper=caller[lo:hi]
        cls.receipt = dict(cases=len(cls.cases),native_cases=len(cls.native_cases),
            installed=cls.installed,matching_credit=int(cls.installed),compiler_only=True,guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('record effect qualification:',cls.receipt)

    def run_model(self, words, case, phase=0, copy=False, delta=0, symbols=None, entry=source.ENTRY):
        connected = {}
        if copy:
            at=(symbols or NAMES)['memcpy']
            connected.update(zip(range(at,at+44,4),self.copy_words))
        if case.wrapper:
            connected.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
            return RecordOracle(self.caller_words,fixture(case,delta),case,phase,delta,symbols,
                                source.CALLER_ENTRY,connected,(RECORD+delta,)).run()
        return RecordOracle(words,fixture(case,delta),case,phase,delta,symbols,entry,connected).run()

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

    def test_direct_C_independent_bindings_and_all_pristine_callers(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(self.original))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),2)
        self.assertEqual(self.words[0],0x27BDFFB8)
        self.assertEqual(self.words[32:35],[0xAFA20044,0x8FA30044,0x00601025])
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
        self.assertEqual(found,[('func_15013F9C',0x15013FA8)])
        self.assertEqual(self.caller_words,[0x27BDFFE8,0xAFBF0014,0x240500FF,opcode,0x24060001,
                                          0x24020001,0x8FBF0014,0x27BD0018,0x03E00008,0])
        self.receipt['all_direct_retail_call_sites']=found

    def test_complete_states_reference_return_spill_alias_and_fired_original_copy(self):
        visits=set();phases=0;fired=set();copies=0;configured=0;wrappers=0;return_aliases=0
        for case in self.cases:
            for phase,copy in itertools.product((0,8),(False,True)):
                expected,events,result=reference(fixture(case),case,phase)
                a=self.run_model(self.truth,case,phase,copy)
                b=self.run_model(self.words,case,phase,copy)
                self.assertEqual(complete(a),complete(b))
                self.assertEqual(public_memory(b.memory),public_memory(expected),case)
                self.assertEqual([e for e in b.events if public_event(e)],events,(case,copy))
                self.assertEqual(b.r[2],result,case)
                self.assertEqual(struct.unpack_from('>3I',b.snapshot),(RECORD,case.value,0))
                self.assertEqual(b.snapshot[12],case.selector&255)
                if case.allocated:
                    at=b.main_sp_entry-72+0x34
                    wanted=bytes((0x11,0x22,0x33)) if case.padding_alias else bytes(fixture(case)[at+i] for i in range(13,16))
                    self.assertEqual(b.padding_observed,wanted)
                    if case.destination==2:
                        self.assertNotEqual(result,destination(case,at)-0x28)
                        return_aliases+=1
                self.assertEqual(source.COPY in b.visits,bool(copy and case.allocated))
                copies+=source.COPY in b.visits;configured+=copy
                wrappers+=case.wrapper;visits.update(b.visits);fired.update(b.fired);phases+=1
        for entry,size in ((source.ENTRY,156),(source.COPY,44),(source.CALLER_ENTRY,40)):
            self.assertTrue(set(range(entry,entry+size,4))<=visits)
        self.assertEqual(fired,{'payload-reserved','all-incoming-homes'})
        self.assertGreater(return_aliases,0)
        self.receipt.update(complete_final_states=phases,model_variant_phases=phases,
            configured_memcpy_phases=configured,connected_original_memcpy_phases=copies,
            original_C_wrapper_phases=wrappers,fired_saved_result_overlap_phases=return_aliases,
            all_39_target_10_caller_11_copy_words_visited=True,
            fired_physical_alias_kinds=sorted(fired),hardware_FCSR_MMU_modeled=False)

    def test_native32_three_optimizations_valid_typed_records_pointer_return_and_wrapper(self):
        for optimization in ('-O0','-O2','-O3'):
            result=self.native(source.SELECTED,'native',optimization)
            self.assertEqual(result.returncode,0,(optimization,result.stdout,result.stderr))
        self.receipt.update(native_optimizations=3,trap_UBSan=True,native_reserved_bytes_unconstrained=True,
                            native_record_word_subobjects=True)

    def test_compiled_semantic_capture_zero_selector_variant_size_copy_and_return_negatives(self):
        value='    payload.value = *(s32 *)((u8 *)source + 0x18);\n'
        selector='    payload.selector = *(s32 *)((u8 *)source + 0x1C);\n'
        def late(assignment):
            return source.SELECTED.replace(assignment,'').replace('    if (effect != 0) {',assignment+'    if (effect != 0) {')
        negatives={
            'late-word':late(value),'late-selector':late(selector),
            'wrong-zero':source.SELECTED.replace('payload.zero = 0','payload.zero = 1'),
            'wrong-selector':source.SELECTED.replace('source + 0x1C','source + 0x18'),
            'wrong-variant':source.SELECTED.replace('16, variant, parameter','16, variant ^ 0x80, parameter'),
            'wrong-size':source.SELECTED.replace('0, 30, 16','0, 30, 12'),
            'short-copy':source.SELECTED.replace('&payload, 16','&payload, 12'),
            'wrong-destination':source.SELECTED.replace('effect + 0x28','effect + 0x24'),
            'copy-result-not-allocation':source.SELECTED.replace('        memcpy(', '        effect = memcpy('),
            'skip-copy':source.SELECTED.replace('if (effect != 0)','if (effect != 0 && payload.zero == 1)'),
        }
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            result=self.native(body,'negative-'+label)
            self.assertEqual(result.returncode,23,(label,result.stdout,result.stderr))
        self.receipt['compiled_semantic_negatives']=len(negatives)

    def test_zeroed_reserved_bytes_and_missing_saved_result_reload_are_effective_guest_negatives(self):
        zero=source.SELECTED.replace('    payload.zero = 0;',
            '    payload.zero = 0;\n    payload.reserved[0] = payload.reserved[1] = payload.reserved[2] = 0;')
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+zero,'zero-reserved')
        self.assertEqual(diagnostic,'')
        raw,_=source.payload(obj);image,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,functions[source.FUNCTION]['value']))
        for phase in (0,8):
            original=self.run_model(self.truth,Case(),phase)
            negative=self.run_model(words,Case(),phase)
            self.assertNotEqual(negative.padding_observed,original.padding_observed)
            self.assertNotEqual(public_memory(negative.memory),public_memory(original.memory))
            wrong=self.truth.copy();self.assertEqual(wrong[33],0x8FA30044);wrong[33]=0
            for copy in (False,True):
                mutated=self.run_model(wrong,Case(),phase,copy)
                self.assertNotEqual(mutated.r[2],original.r[2])
        self.receipt.update(effective_reserved_negative_phases=2,effective_result_reload_negative_phases=4)

    def test_independent_GNU_code_helpers_and_argument_rebases(self):
        count=0
        for i,(code_delta,helper_delta,data_delta) in enumerate((
                (0x10000,0x20000,0x3000),(0x100000,0x30000,-0x10000),(0x2000000,-0x10000,0x8000))):
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
            for case in (Case(),Case(0x80000000,0xFFFFFF80,0xFFFFFFFF,0x80000000,mutate=True),
                         Case(allocated=False),Case(destination=2)):
                for phase in (0,8):
                    a=self.run_model(linked[0],case,phase,True,data_delta,symbols,source.ENTRY+code_delta)
                    b=self.run_model(linked[1],case,phase,True,data_delta,symbols,source.ENTRY+code_delta)
                    self.assertEqual(complete(a),complete(b))
                    expected,_,result=reference(fixture(case,data_delta),case,phase,data_delta)
                    self.assertEqual(public_memory(a.memory,data_delta),public_memory(expected,data_delta))
                    self.assertEqual(a.r[2],result)
                    count+=1
        self.receipt.update(independent_GNU_rebase_plans=3,rebased_phases=count)

    def test_actual_full_owners_Make_and_strict_first_image_scope(self):
        report=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((report['preserved_neighbors'],report['preserved_raw_caller_functions']),(51,32))
        self.assertTrue(report['inherited_owner_diagnostics_unchanged'])
        self.assertTrue(report['isolated_diagnostics_empty'])
        make=json.loads((self.output/'make-shadow.json').read_text())
        self.assertEqual((make['actual_Make_commands'],make['preserved_padded_caller_functions']),(8,32))
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
        self.receipt.update(preserved_neighbors=51,preserved_caller_functions=32,wrong_image_controls=8)

    def test_live_inputs_frozen_history_typed_caller_and_no_new_guards(self):
        caller=source.recovered_caller(self.values[source.CALLER].decode())
        self.assertIn('void *func_151CD2C0(void *source, u8 variant, s32 parameter);',caller)
        self.assertIn('s32 func_15013F9C(void *source)',caller)
        if self.installed:
            self.assertTrue(source.audit(ROOT,self.output)['strict_first_link_reproduced'])
        else:
            for name,old in self.values.items():self.assertEqual((ROOT/name).read_bytes(),old,name)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])


if __name__=='__main__':
    unittest.main()
