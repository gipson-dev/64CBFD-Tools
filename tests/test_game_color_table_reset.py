"""Color/table reset: eight-word ABI, typed pointer slots and closed address fold."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_color_table_reset as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
OLD, VIEW, STATUS, SLOTS = 0x800D9894, 0x800BE9E8, 0x800D9890, 0x800D9898
RECORD, OUTPUT, PREVIOUS, ROUTE_RECORD = 0x31000, 0x30000, 0x32000, 0x33000
REMOVE, CREATE, SLOT_UPDATE, FALLBACK, LOWER_REMOVE = 0x1516972C, 0x151A4FD0, 0x151696DC, 0x15169804, 0x15168B10
ALLOCATE, HEAP, INITIALIZE, CALLBACK = 0x15167A68, 0x10003C6C, 0x15168A4C, 0x15500100
CAPTURE_COUNT, CAPTURE_SLOTS, CALLBACK_TABLE = 0x800DD190, 0x800DD198, 0x8008B4D0
HEAD = 0x800DCE50 + 0x5A * 4
DISPATCH, DISPATCH_ROM, WINDOW, JOIN = 0x150B6BC0, 0xE4070, 0x15174A2C, 0x15174A58
TABLE, JUMPS = 0x8008CD04, 0x8009FD00
SYMBOLS = dict(D_800D9894=OLD, D_800BE9E8=VIEW, D_800D9890=STATUS,
    D_800D9898=SLOTS, D_800D989C=SLOTS+4, D_800D98A0=SLOTS+8, D_800D98C0=SLOTS+40,
    func_1516972C=REMOVE, func_151A4FD0=CREATE)
WORDS = (0, 1, 255, 256, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xAABBCCDD)


@dataclass(frozen=True)
class Case:
    old: int = RECORD
    view: int = 0xAABBCCDD
    fail: bool = False
    mode: int = 0
    result: int = OUTPUT
    seed: int = 0xA5
    alias: object = None
    node_type: int = 0x5A
    captured: int = 4
    callback: bool = False
    head: bool = False


def corpus():
    for old, view, fail, mode, result in itertools.product(
            (0, RECORD), WORDS, (False, True), range(4), (OUTPUT, RECORD, 0xFFFFFFFF)):
        yield Case(old, view, fail, mode, result, (view ^ result ^ mode) & 255)
    for i in range(64):
        yield Case(RECORD if i & 1 else 0, (i*1664525+1013904223)&0xFFFFFFFF,
            bool(i&2), i&3, OUTPUT, i)
    for alias, view, fail, mode in itertools.product(
            ('old-slot0', 'state-slot1', 'view-slot5'), (0xFFFFFFFF, 0x80000000), (False, True), (0, 3)):
        yield Case(view=view, fail=fail, mode=mode, alias=alias)


def anchors(case, symbols=None):
    result = dict(symbols or SYMBOLS)
    if case.alias == 'old-slot0':
        result['D_800D9894'] = result['D_800D9898']
    elif case.alias == 'state-slot1':
        result['D_800D9890'] = result['D_800D9898'] + 4
    elif case.alias == 'view-slot5':
        result['D_800BE9E8'] = result['D_800D9898'] + 20
    return result


def fixture(case, symbols=None):
    s = anchors(case, symbols)
    memory = {STACK+i: (i*17+0xA5)&255 for i in range(-0x1000, 0x400)}
    regions = ((s['D_800D9898']-32, 112), (s['D_800D9894']-16, 36),
        (s['D_800D9890']-16, 36), (s['D_800BE9E8']-16, 36),
        (RECORD-16, 96), (OUTPUT-16, 144), (PREVIOUS-16, 64),
        (ROUTE_RECORD-16, 64), (CAPTURE_COUNT-8, 64), (TABLE, 112), (JUMPS, 40),
        (CALLBACK_TABLE+case.node_type*52, 4), (HEAD-16, 36), (0x800B0DF0, 4))
    for base, size in regions:
        for i in range(size):
            memory.setdefault(base+i, (case.seed+i*13+0x45)&255)
    for i in range(10):
        put(memory, s['D_800D9898']+i*4, (0xB1000000+i*0x10203+case.seed)&0xFFFFFFFF)
    put(memory, s['D_800D9894'], case.old)
    put(memory, s['D_800BE9E8'], case.view)
    for i in range(4):
        memory[s['D_800D9890']+i] = (case.seed+i*13+0x45)&255
    memory[RECORD] = case.node_type
    put(memory, RECORD+8, PREVIOUS)
    memory[CAPTURE_COUNT] = case.captured & 255
    for i in range(4):
        put(memory, CAPTURE_SLOTS+i*4, RECORD if i&1 else PREVIOUS)
    put(memory, CALLBACK_TABLE+case.node_type*52, CALLBACK if case.callback else 0)
    put(memory, HEAD, PREVIOUS if case.head else 0)
    put(memory, 0x800B0DF0, ROUTE_RECORD)
    memory[ROUTE_RECORD+0xB] = 5
    return memory


def public(memory):
    return {at: value for at, value in memory.items() if not STACK-0x1000 <= at < STACK+0x400}


def snapshot(memory, symbols):
    return (read(memory, symbols['D_800D9894']), read(memory, symbols['D_800BE9E8']),
        memory[symbols['D_800D9890']], *(read(memory, symbols['D_800D9898']+i*4) for i in range(10)))


def mutate(memory, case, stage, symbols):
    if case.mode & stage:
        put(memory, symbols['D_800BE9E8'], read(memory, symbols['D_800BE9E8']) ^ (0x12345678 if stage==1 else 0xA5A55A5A))
        put(memory, symbols['D_800D9894'], 0x41000000 | case.seed | (stage<<16))
        memory[symbols['D_800D9890']] = 0xE0 | stage
        put(memory, symbols['D_800D9898']+((case.seed+stage)%10)*4, 0xC0000000 | stage)


def reference(case, symbols=None, real=False, memory=None):
    s = anchors(case, symbols)
    m = dict(fixture(case, s) if memory is None else memory)
    calls, packets, seen = [], [], []
    old = read(m, s['D_800D9894'])
    if old:
        calls.append((s['func_1516972C'], (old,)))
        if real:
            calls.append((SLOT_UPDATE, (old,)))
            count = m[CAPTURE_COUNT]
            count = count-256 if count & 128 else count
            for i in range(max(0, count)):
                if read(m, CAPTURE_SLOTS+i*4) == old:
                    put(m, CAPTURE_SLOTS+i*4, read(m, old+8))
            if m[old] >= 2:
                callback = read(m, CALLBACK_TABLE+m[old]*52)
                if callback:
                    calls.append((callback, (old,)))
                else:
                    calls.extend(((FALLBACK, (old,)), (LOWER_REMOVE, (old, 1))))
                mutate(m, case, 1, s)
        else:
            mutate(m, case, 1, s)
    view = read(m, s['D_800BE9E8'])
    args = (0, 0, 255, 0, 0, view, 0, 0)
    packets.append(args); seen.append(snapshot(m, s))
    calls.append((s['func_151A4FD0'], args))
    result = 0 if case.fail else case.result
    if real:
        calls.extend(((ALLOCATE, (0x5A, 0, 32, 0, 255, 1)), (HEAP, (32, 1, 0, 0, 1))))
        mutate(m, case, 2, s)
        if result:
            calls.append((INITIALIZE, (result, 0x5A)))
            m[result+1] = 0
            head = read(m, HEAD)
            put(m, result+8, head)
            if head:
                put(m, head+4, result)
            m[result] = 0x5A
            put(m, result+4, 0); put(m, HEAD, result); m[result+0xC] = 255
            put(m, result+0x10, 0)
            for offset, value in ((0x14, 0), (0x15, 255), (0x16, 0), (0x17, 0),
                    (0x18, 0), (0x19, 0), (0x1A, view & 255)):
                m[result+offset] = value
    else:
        mutate(m, case, 2, s)
    put(m, s['D_800D9894'], result)
    m[s['D_800D9890']] = 3
    for i in range(10):
        put(m, s['D_800D9898']+i*4, 0)
    return m, calls, packets, seen


class ResetOracle(TimingOracle):
    def __init__(self, words, case, phase=0, symbols=None, entry=source.ENTRY,
            connected=None, real=False, memory=None, window=False):
        self.case, self.reset_symbols, self.real = case, anchors(case, symbols), real
        self.packets, self.seen, self.visits = [], [], set()
        self.target_sp, self.boundary_hit = STACK+phase, None
        super().__init__(words, fixture(case, self.reset_symbols) if memory is None else memory,
            phase=phase, entry=entry, arguments=(0x87650000 | case.seed,), connected=connected)
        if window:
            self.r[29] -= 24
            put(self.memory, self.r[29]+0x1C, 0x87650000 | case.seed)
            self.code = ReturnBoundaryCode(self.code, JOIN, self)

    def execute(self, word):
        self.visits.add(self.current_pc)
        op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
        if op==32:
            imm=(word&65535)-(65536 if word&0x8000 else 0)
            value=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
            self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
        elif op==0 and word&63==42:
            left,right=self.r[rs],self.r[rt]
            left=left-0x100000000 if left&0x80000000 else left
            right=right-0x100000000 if right&0x80000000 else right
            self.r[rd]=int(left<right);self.r[0]=0
        else:
            super().execute(word)

    def record_call(self, target):
        signatures = {self.reset_symbols['func_1516972C']: 1, self.reset_symbols['func_151A4FD0']: 8,
            SLOT_UPDATE: 1, FALLBACK: 1, LOWER_REMOVE: 2, CALLBACK: 1,
            ALLOCATE: 6, HEAP: 5, INITIALIZE: 2, DISPATCH: 1, source.ENTRY: 0}
        if target not in signatures:
            raise AssertionError(('Unbounded reset provider', hex(target)))
        args = self.arguments(signatures[target])
        self.calls.append((target, args)); self.events.append(('CALL', target, args))
        if target == self.reset_symbols['func_151A4FD0']:
            self.packets.append(args); self.seen.append(snapshot(self.memory, self.reset_symbols))

    def hook(self, target):
        result = 0x87654321
        if target == self.reset_symbols['func_1516972C'] and not self.real:
            mutate(self.memory, self.case, 1, self.reset_symbols)
        elif target in (CALLBACK, LOWER_REMOVE):
            mutate(self.memory, self.case, 1, self.reset_symbols)
        elif target == self.reset_symbols['func_151A4FD0'] and not self.real:
            mutate(self.memory, self.case, 2, self.reset_symbols)
            result = 0 if self.case.fail else self.case.result
        elif target == HEAP:
            mutate(self.memory, self.case, 2, self.reset_symbols)
            result = 0 if self.case.fail else self.case.result
        else:
            raise AssertionError(('Unexpected reset boundary', hex(target)))
        for i in range(4):
            self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = result


def native_vector(case, final):
    initial = fixture(case)
    if final:
        memory, calls, packets, seen = reference(case)
    else:
        memory, calls, packets, seen = initial, [], [], []
    fence = lambda i: (0xA5000000 | (case.seed<<8) | i)
    data = [fence(i) for i in range(4)]
    data += [read(memory, OLD), read(memory, VIEW)]
    data += [sum(memory[STATUS+i]<<(8*i) for i in range(4))]
    data += [read(memory, SLOTS+i*4) for i in range(10)]
    data += [fence(i+4) for i in range(4)]
    data += list(packets[0] if packets else (0,)*8)
    data += list(seen[0] if seen else (0,)*13)
    removed = [args[0] for target,args in calls if target == REMOVE]
    data += [removed[0] if removed else 0, len(removed), len(packets)]
    assert len(data) == 45
    return data


def native_harness(body, cases):
    row = lambda values: '{' + ','.join('0x%08Xu' % value for value in values) + '}'
    rows = ['{%d,%d,0x%08Xu,%d,%s,%s}' % (c.mode, c.fail, c.result, c.seed,
        row(native_vector(c, False)), row(native_vector(c, True))) for c in cases]
    return """typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
#define NULL ((void *)0)
typedef struct{u32 before[4];void *old;s32 view;u8 status[4];void *slots[10];u32 after[4];
 u32 packet[8],seen[13],removed,removeCalls,createCalls;}State;
typedef char Width[(sizeof(void*)==4&&sizeof(State)==180&&__builtin_offsetof(State,slots)==28&&__builtin_offsetof(State,packet)==84)?1:-1];
typedef struct{u32 mode,fail,result,seed,initial[45],expected[45];}Case;
static const Case cases[]={""" + ',\n'.join(rows) + """};
static State state;static const Case *item;
#define D_800D9894 state.old
#define D_800BE9E8 state.view
#define D_800D9890 state.status[0]
#define D_800D9898 ((u8*)state.slots)
#define D_800D98A0 ((u8*)(state.slots+2))
#define D_800D98C0 ((u8*)(state.slots+10))
static void mutation(u32 stage){if(item->mode&stage){u32 i=(item->seed+stage)%10;
 state.view=(s32)((u32)state.view^(stage==1?0x12345678u:0xA5A55A5Au));
 state.old=(void*)(0x41000000u|item->seed|(stage<<16));state.status[0]=(u8)(0xE0u|stage);
 state.slots[i]=(void*)(0xC0000000u|stage);}}
static void func_1516972C(void *old){state.removed=(u32)old;state.removeCalls++;mutation(1);}
static void *func_151A4FD0(s32 selector,u32 value,s32 red,s32 green,s32 blue,s32 view,u8 callback,u32 extra){
 u32 i;u32 words[8]={(u32)selector,value,(u32)red,(u32)green,(u32)blue,(u32)view,callback,extra};
 for(i=0;i<8;i++)state.packet[i]=words[i];
 state.seen[0]=(u32)state.old;state.seen[1]=(u32)state.view;state.seen[2]=state.status[0];
 for(i=0;i<10;i++)state.seen[3+i]=(u32)state.slots[i];
 state.createCalls++;mutation(2);return item->fail?NULL:(void*)item->result;}
""" + body + """
static int run(void){u32 n,i,j;u8 *p=(u8*)&state;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){item=&cases[n];
  for(i=0;i<45;i++)for(j=0;j<4;j++)p[4*i+j]=(u8)(item->initial[i]>>(8*j));
  func_150B6C90();
  for(i=0;i<45;i++)for(j=0;j<4;j++)if(p[4*i+j]!=(u8)(item->expected[i]>>(8*j)))return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ColorTableResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT/source.BUILD
        cls.installed = source.digest((ROOT/source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            source.freeze(ROOT, cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT, cls.output); source.make_shadow(ROOT, cls.output); source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output); cls.rom = cls.values['conker/conker.us.bin']
        cls.obj, diag = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED, 'fresh-selected')
        if diag:
            raise ValueError(diag)
        data, fs = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.raw = list(struct.unpack_from('>42I', data, fs[source.FUNCTION]['value']))
        data, fs = source.link_owner(ROOT, cls.output, cls.output/'qualified-padded.o', source.OWNER)
        cls.fitted = list(struct.unpack_from('>41I', data, fs[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>41I', cls.rom, source.ROM))
        cls.cases = list(corpus()); cls.native_cases = [c for c in cls.cases if c.alias is None]
        cls.connected = {}
        for entry, words in ((REMOVE,28),(SLOT_UPDATE,20),(FALLBACK,8),(CREATE,40),(ALLOCATE,28),(INITIALIZE,20)):
            start = entry-0x15000000+0x2D4B0
            cls.connected.update(zip(range(entry,entry+words*4,4),struct.unpack_from('>%dI'%words,cls.rom,start)))
        cls.receipt = dict(installed=cls.installed, cases=len(cls.cases), native_cases=len(cls.native_cases), guards=17)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('color/table reset qualification:', cls.receipt)

    def test_01_extent_profile_bindings_original_and_actual_old_stub(self):
        raw, bindings = source.payload(self.obj); fitted, rels = source.normalized(raw, bindings)
        self.assertEqual((len(raw), self.raw[0], len(fitted)), (168,0x27BDFFD8,164))
        self.assertEqual((sum(map(len,bindings.values())),sum(map(len,rels.values()))),(16,17))
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(fitted,rels))
        self.assertEqual(self.truth,self.fitted)
        q = json.loads((self.output/'qualification.json').read_text())
        self.assertTrue(q['retail_no_unroll']); self.assertGreater(q['preserved_neighbors'],0)
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],3)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.ENTRY,164)
        old=list(struct.unpack_from('>41I',before,at));c=Case()
        self.assertNotEqual(public(ResetOracle(old,c).run().memory),public(reference(c)[0]))
        self.receipt.update(words=41,raw_words=42,frame=40,raw_bindings=16,bindings=17,
            compiler_only=False,guards=17,omitted_address_words=1,inserted_words=0,
            preserved_neighbors=q['preserved_neighbors'],actual_Make_commands=3,old_stub_effectively_rejected=True)

    def compare(self, case, phase=0, symbols=None, images=None, entry=source.ENTRY, real=False):
        expected,calls,packets,seen=reference(case,symbols,real)
        models=[]
        for words in images or (self.truth,self.raw,self.fitted):
            m=ResetOracle(words,case,phase,symbols,entry,
                self.connected if real else None,real).run()
            self.assertEqual((public(m.memory),m.calls,m.packets,m.seen),(public(expected),calls,packets,seen))
            self.assertEqual(m.r[29],STACK+phase)
            models.append(m)
        self.assertEqual(complete(models[0]),complete(models[2]))
        for reg in (*range(16,24),28,29,30,31):
            self.assertEqual(models[0].r[reg],models[1].r[reg])
        return models

    def test_02_complete_semantics_ordering_and_guest_aliases(self):
        original_visits=set();raw_visits=set()
        aliases={}
        for c,phase in itertools.product(self.cases,(0,8)):
            images=None
            if c.alias is not None:
                if c.alias not in aliases:
                    aliases[c.alias]=self.gnu_images(anchors(c),source.ENTRY,'alias-'+c.alias)
                images=aliases[c.alias]
            models=self.compare(c,phase,images=images)
            original_visits.update(models[0].visits);raw_visits.update(models[1].visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+164,4))<=original_visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+168,4))<=raw_visits)
        self.receipt.update(model_phases=len(self.cases)*2,guest_only_phases=sum(c.alias is not None for c in self.cases)*2,
            all41_fitted_and42_raw_words_executed=True,raw_private_caller_saved_identity_not_claimed=True,
            captured_view_after_remove=True,null_factory_still_resets=True)
        self.receipt['alias_GNU_links']=len(aliases)*3

    def native(self,body,label,opt='-O2'):
        path=self.output/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.native_cases))
        subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fno-builtin','-mstackrealign','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,check=True)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_typed_pointer_slots_and_effective_controls(self):
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        b=source.SELECTED
        controls={
            'missing-remove':b.replace('        func_1516972C(D_800D9894);',''),
            'early-view':b.replace('    void **current;','    void **current;\n    s32 captured = D_800BE9E8;').replace('0, 0, D_800BE9E8, 0, 0','0, 0, captured, 0, 0'),
            'truncated-view':b.replace('0, 0, D_800BE9E8, 0, 0','0, 0, (u8)D_800BE9E8, 0, 0'),
            'wrong-red':b.replace('(0, 0, 255, 0, 0,','(0, 0, 254, 0, 0,'),
            'wrong-callback':b.replace('D_800BE9E8, 0, 0)','D_800BE9E8, 1, 0)'),
            'wrong-extra':b.replace('D_800BE9E8, 0, 0)','D_800BE9E8, 0, 4)'),
            'early-old-clear':b.replace('        func_1516972C(D_800D9894);','        D_800D9894 = NULL;\n        func_1516972C(D_800D9894);'),
            'missing-status':b.replace('    D_800D9890 = 3;',''),
            'wide-status':b.replace('    D_800D9890 = 3;','    D_800D9890 = 3;\n    ((u8 *)&D_800D9890)[1] = 0;\n    ((u8 *)&D_800D9890)[2] = 0;\n    ((u8 *)&D_800D9890)[3] = 0;'),
            'missing-pair':b.replace('    ((void **)D_800D9898)[0] = NULL;',''),
            'missing-tail-slot':b.replace('        current[3] = NULL;',''),
            'null-early-return':b.replace('    D_800D9890 = 3;','    if (D_800D9894 == NULL) return;\n    D_800D9890 = 3;'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,b,name);self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,typed_fenced_pointer_array=True,
            compiled_semantic_negatives=len(controls),native_pointer_bits_not_heap_validity_claims=True)

    def test_04_actual_factory_and_release_wrappers_bounded_lower_providers(self):
        visits=set();phases=0
        for old,node_type,fail,callback,head,phase in itertools.product(
                (0,RECORD),(0,1,2,0x5A),(False,True),(False,True),(False,True),(0,8)):
            c=Case(old=old,node_type=node_type,fail=fail,callback=callback,head=head,mode=3,captured=4)
            models=self.compare(c,phase,real=True);visits.update(models[0].visits);phases+=1
        self.assertTrue(set(self.connected)<=visits)
        self.receipt.update(original_helper_words=144,all144_helper_words_executed=True,real_chain_phases=phases,
            callback_and_lower_heap_remove_providers_bounded=True,complete_heap_or_free_behavior_not_claimed=True)

    def test_05_actual_slot5_window_and_full_52_word_dispatcher(self):
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))],[0xE40A8])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)],[])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',DISPATCH)],[0x2317D8])
        dispatcher=list(struct.unpack_from('>52I',self.rom,DISPATCH_ROM))
        window=list(struct.unpack_from('>11I',self.rom,0x1A1EDC));phases=joins=0
        for state,slot,old,fail,phase in itertools.product((0,1,3,255),(0,5),(0,RECORD),(False,True),(0,8)):
            c=Case(old=old,fail=fail,mode=3);memory=fixture(c)
            memory[STATUS]=state;memory[ROUTE_RECORD+0xB]=slot
            for i,value in enumerate(struct.unpack_from('>28I',self.rom,0x2317C4)):put(memory,TABLE+i*4,value)
            for i,value in enumerate(struct.unpack_from('>10I',self.rom,0x2447C0)):put(memory,JUMPS+i*4,value)
            active=slot==5 and state==1
            if active:expected,calls,packets,seen=reference(c,memory=memory)
            else:expected,calls,packets,seen=dict(memory),[],[],[]
            models=[]
            for image in (self.truth,self.raw,self.fitted):
                connected=dict(zip(range(DISPATCH,DISPATCH+208,4),dispatcher))
                connected.update(zip(range(source.ENTRY,source.ENTRY+len(image)*4,4),image))
                m=ResetOracle(window,c,phase,entry=WINDOW,connected=connected,memory=memory,window=True)
                with self.assertRaises(CallerBoundary):m.run()
                self.assertEqual(m.boundary_hit,JOIN);self.assertEqual(m.r[29],STACK+phase-24)
                filtered=[call for call in m.calls if call[0]not in (DISPATCH,source.ENTRY)]
                self.assertEqual((public(m.memory),filtered,m.packets,m.seen),(public(expected),calls,packets,seen))
                models.append(m);joins+=1
            self.assertEqual(complete(models[0]),complete(models[2]));phases+=1
        self.receipt.update(target_direct_site='150B6BF8',dispatcher_literal_ROM='2317D8',slot=5,
            outer_window_words=11,complete_dispatcher_words=52,caller_phases=phases,fired_join_boundaries=joins,
            outer_full_parent_not_claimed=True,void_result_not_consumed=True,other_dispatch_cases_not_executed=True)

    def test_06_guard_controls_and_closed_address_fold(self):
        raw,bindings=source.payload(self.obj);fitted,tags=source.normalized(raw,bindings)
        self.assertEqual((len(raw),len(fitted)),(168,164))
        self.assertEqual(len(source.GUARDS),17);self.assertEqual(sum(row[5]for row in source.GUARDS),1)
        prefix=self.values['conker/retail_word_patches.us.csv'];guarded=source.guard_bytes(self.values)
        self.assertTrue(guarded.startswith(prefix));self.assertEqual(guarded.count(b'\n')-prefix.count(b'\n'),17)
        suffix=list(csv.DictReader(io.StringIO(prefix.splitlines()[0].decode()+'\n'+guarded[len(prefix):].decode())))
        controls=0
        for i,row in enumerate(suffix):
            wrong=bytearray(raw);wrong[int(row['offset'],0)]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(wrong),bindings)
            for field in ('expected','expected_relocations'):
                rows=[dict(r)for r in suffix]
                rows[i][field]='0x%08X'%(int(rows[i][field],0)^1)if field=='expected'else 'R_MIPS_HI16:wrong_symbol'
                text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(rows[0]),lineterminator='\n');writer.writerows(rows)
                path=self.output/('bad-guard-%d-%s.csv'%(i,field));path.write_bytes(prefix+text.getvalue().encode())
                with self.assertRaises(ValueError):source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
                controls+=1
            rows=[dict(r)for r in suffix]
            if rows[i]['omit']=='true':rows[i]['omit']='false'
            else:rows[i]['replacement']='0x%08X'%(int(rows[i]['replacement'],0)^1)
            text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(rows[0]),lineterminator='\n');writer.writerows(rows)
            path=self.output/('bad-replacement-%d.csv'%i);path.write_bytes(prefix+text.getvalue().encode())
            if row['omit']=='true':
                with self.assertRaises(ValueError):source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
            else:
                asm=self.output/('bad-replacement-%d.s'%i);obj=asm.with_suffix('.o')
                asm.write_text(source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER))
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
                data,fs=source.link_owner(ROOT,self.output,obj,source.OWNER)
                self.assertNotEqual(data[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+164],self.rom[source.ROM:source.ROM+164])
            controls+=1
        self.receipt.update(guard_controls=controls,raw_word_corruption_controls=17,one_address_fold=True,
            closed_loop_allocation_and_setup_schedule=True,old_guard_prefix_preserved=True)

    def gnu_images(self,symbols,entry,label):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.output);images=[]
        for kind,obj in (('original',original),('raw',self.obj),('fitted',self.output/'qualified-padded.o')):
            data,fs,rs=source.parse_object(obj)
            text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
            self.assertEqual(unknown,[]);stem=self.output/(label+'-'+kind)
            asm=stem.with_suffix('.s');compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
            asm.write_text(text);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
            images.append(list(struct.unpack_from('>%dI'%(42 if kind=='raw'else 41),sections(elf)['.text'][1])))
        self.assertEqual(images[0],images[2])
        return images

    def test_07_independent_GNU_rebases_and_pair_boundary_gate(self):
        phases=0
        for index,base in enumerate((SLOTS,0x80347FF8,0x80358000,0x8036FFF8)):
            symbols=dict(SYMBOLS)
            if index:
                symbols.update(D_800D9898=base,D_800D989C=base+4,D_800D98A0=base+8,D_800D98C0=base+40,
                    D_800D9894=0x80418004+index*0x10000,D_800D9890=0x80527FFF+index*0x10000,
                    D_800BE9E8=0x80638000+index*0x10000,func_1516972C=REMOVE+index*0x10000,
                    func_151A4FD0=CREATE+index*0x10000)
            source.validate_layout(symbols);entry=source.ENTRY if not index else 0x17007FFC+index*0x10000
            images=self.gnu_images(symbols,entry,'rebase-%d'%index)
            for old,fail,mode,phase in itertools.product((0,RECORD),(False,True),(0,3),(0,8)):
                self.compare(Case(old=old,fail=fail,mode=mode),phase,symbols,images,entry);phases+=1
        bad=dict(SYMBOLS);base=0x80347FFC
        bad.update(D_800D9898=base,D_800D989C=base+4,D_800D98A0=base+8,D_800D98C0=base+40)
        with self.assertRaises(ValueError):source.validate_layout(bad)
        wrong=dict(SYMBOLS);wrong['D_800D989C']+=4
        with self.assertRaises(ValueError):source.validate_layout(wrong)
        prefixes=0
        for c,phase in itertools.product((Case(old=0),Case(mode=3)),(0,8)):
            good=ResetOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[ResetOracle(code,c,phase)for code in (self.truth,self.fitted)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));prefixes+=1
        self.receipt.update(independent_GNU_links=12,rebase_phases=phases,target_fault_prefixes=prefixes,
            shared_adjusted_HI16_pair_boundary_rejected=True,arbitrary_pair_placement_not_claimed=True,
            portable_C_fault_or_hardware_claimed=False)

    def test_08_strict_image_and_frozen_installed_input_history(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+164]
        predicted=source.predicted_image(before,truth);at=source.elf_slot_offset(before,source.ENTRY,164)
        self.assertEqual((self.output/'first-linked.elf').read_bytes(),predicted)
        entries={name:(offset,string) for offset,name,_,string in source.symbol_rows(before)}
        offsets=[0,at-1,at,at+160,at+164,len(before)-1]
        for names in source.SYMBOL_ORDER:
            offsets.extend(entries[names[0]])
        for offset in offsets:
            bad=bytearray(predicted);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=(self.output/('before-'+name.replace('/','_'))).read_bytes();self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else (
                predicted if self.installed and name=='conker/build/conker.us.elf'else (
                source.guard_bytes(self.values)if self.installed and name=='conker/retail_word_patches.us.csv'else old))
            self.assertEqual((ROOT/name).read_bytes(),expected)
        self.assertEqual(source.digest((self.output/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_negatives=len(offsets)+1,metadata_symbol_name_groups=2,
            live_inputs=len(source.INPUTS),old_padded_object_pinned=True)
