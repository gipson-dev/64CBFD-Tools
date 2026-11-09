"""Direct clock advance: source, independent contracts, callers and native32."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_sequence_time_advance_1501e400_match as match
from tools.tests import game_sequence_time_advance_1501e400_oracle as guest
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_frame_sequence_oracle as frame
from tools.tests import game_sequence_catchup_oracle as catchup
ROOT=match.ROOT

def controls():
    b=match.SELECTED
    pairs={
        'count_underflow':('if (D_800C3A58 != 0) D_800C3A58--;','D_800C3A58--;'),
        'active_nonzero':('D_800C35EA[slot] == 1','D_800C35EA[slot] != 0'),
        'missing_previous':('    D_800C35B8[slot] = D_800C35B0[slot];\n',''),
        'wrong_slot_gate':('slot != 0 ||','slot == 0 ||'),
        'pause_inverted':('D_800BEAC0 == 0','D_800BEAC0 != 0'),
        'no_increment':('(u32)D_800C35B0[slot] + (u32)D_800BEA08','(u32)D_800C35B0[slot]'),
        'wrong_increment':('(u32)D_800BEA08','(u32)D_800BEA08 + 1U'),
        'signed_marker':('(u16)D_800C3C8E','D_800C3C8E'),
        'inverted_marker_gate':('D_800C35C0[slot] == 0','D_800C35C0[slot] != 0'),
        'inverted_previous_test':('(u16)D_800C3C8E == D_800C35B8[slot]','(u16)D_800C3C8E != D_800C35B8[slot]'),
        'inverted_current_test':('(u16)D_800C3C8E != D_800C35B0[slot]','(u16)D_800C3C8E == D_800C35B0[slot]'),
        'wrong_sentinel':('D_800C35B8[slot] = -1','D_800C35B8[slot] = 0'),
        'audio_nonzero':('func_151F2CDC() == 1','func_151F2CDC() != 0'),
        'missing_audio_poll':('func_151F2CDC() == 1','1'),
        'unsigned_clamp':('D_800C35B0[slot] >= D_800C3640[slot]','(u32)D_800C35B0[slot] >= (u32)D_800C3640[slot]'),
        'minimum_clamp':('D_800C35B0[slot] >= D_800C3640[slot]','D_800C35B0[slot] <= D_800C3640[slot]'),
        'missing_update_call':('        func_1501E1B4(slot);\n',''),
    }
    result={n:b.replace(a,z)for n,(a,z)in pairs.items()}
    assert all(v!=b for v in result.values())
    return result

def linked(obj,entry,label,out,s=None):
    s=guest.S if s is None else s;text,fs,refs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(text,f,refs,match.FUNCTION,s);assert not unknown;p=out/label
    p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
    return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def code(words,entry=match.ENTRY):return dict(zip(range(entry,entry+4*len(words),4),words))

def provider(machine,c,t):
    names=('func_1501E1B4','func_151F2CDC','func_15080228');kind=names.index(next(n for n in names if guest.S[n]==t))+1
    guest.effect(machine.memory,c,guest.S,kind)
    for i in range(4):machine.put(guest.u32(machine.r[29]+i*4),0xB5000000+i,4)
    for reg in(1,2,3,*range(4,16),24,25):machine.r[reg]=0xA5000000+reg
    machine.f[:20]=[0xA5000000+i for i in range(20)];machine.hi,machine.lo=0xA5000010,0xA5000011;machine.r[2]=guest.u32(c.poll if kind==2 else 0x81234560)

class ClockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>80I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);assert cls.raw==cls.truth
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_complete_owners_actual_Make_and_strict_image(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(80,40,0,56,56,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions']),(3,57,255,0));self.assertEqual((q['caller']['functions'],q['caller']['diagnostics'],q['caller']['actual_Make']['commands']),(16,3,3));self.assertTrue(q['caller']['padded_object_unchanged'])
        blob,refs=match.payload(self.out/'qualified-owner.o')
        for i in range(320):
            altered=bytearray(blob);altered[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(altered),refs)
        for at in refs:
            altered=dict(refs);altered[at]=[(refs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):match.checked(blob,altered)
        a,b=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for i in(0x80,len(b)-1,match.elf_slot_offset(a,match.ENTRY,320)):
            altered=bytearray(b);altered[i]^=1
            with self.assertRaises(ValueError):match.strict_image(a,bytes(altered),self.rom[match.ROM:match.ROM+320])
        wrong_truth=bytearray(self.rom[match.ROM:match.ROM+320]);wrong_truth[0]^=1
        with self.assertRaises(ValueError):match.strict_image(a,b,bytes(wrong_truth))
    def test_02_independent_state_and_provider_contract(self):
        visited=set();count=accesses=0
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);pair=[]
            for words in(self.truth,self.raw):
                m=guest.Oracle(words,initial,c).run();self.assertEqual((guest.public(m.memory),m.calls,m.snapshots),expected,c);pair.append(m);visited.update(m.visits)
            self.assertEqual((pair[0].memory,pair[0].trace,pair[0].r,pair[0].f,pair[0].hi,pair[0].lo),(pair[1].memory,pair[1].trace,pair[1].r,pair[1].f,pair[1].hi,pair[1].lo));count+=1;accesses+=len(pair[0].trace)
        self.assertEqual((count,len(visited)),(3442,80));self.receipt('guest-contract',dict(cases_per_body=count,visited_words=80,accesses_per_body=accesses,raw_full_literal_state_equal=True))
    def test_03_independent_GNU_rebases_aliases_and_fault_prefixes(self):
        selected=[guest.Case(),guest.Case(active=0,count=0),guest.Case(slot=1,mutation=2,marker=65535,time=65535),guest.Case(mutation=4,poll=1),guest.Case(slot=1,mutation=5,poll=1),guest.Case(mutation=3,paused=0),guest.Case(time=0x7FFFFFFF,delta=1,limit=0x80000000),guest.Case(time=0xFFFFFFFF,limit=0)]
        n=0
        for index in range(6):
            s=dict(guest.S);base=0x30000000+index*0x100000+(0x7FF0 if index&1 else 0xFFE0)
            for j,name in enumerate(n for n in s if n.startswith('D_')):s[name]=base+j*0x10010
            for j,name in enumerate(n for n in s if n.startswith('func_')):s[name]=0x15100000+index*0x10000+j*0x100
            entry=match.ENTRY+index*0x20000;ws=linked(self.out/'qualified-owner.o',entry,'rebase-'+str(index),self.out,s);self.assertEqual(ws,bound_blob(self.prepared['raw'],self.prepared['refs'],s))
            for c in selected:
                initial=guest.fixture(c,s);m=guest.Oracle(ws,initial,c,s,entry).run();self.assertEqual((guest.public(m.memory),m.calls,m.snapshots),guest.reference(initial,c,s));n+=1
        aliases=({'D_800C35B8':guest.S['D_800C35B0']},{'D_800C35C0':guest.S['D_800C35EA']},{'D_800C3A58':guest.S['D_800BEAC0']},{'D_800C3640':guest.S['D_800C35B8']},{'D_800C3C8E':guest.S['D_800C35B8']+2})
        for override in aliases:
            s={**guest.S,**override};ws=bound_blob(self.prepared['raw'],self.prepared['refs'],s)
            for c in selected:
                initial=guest.fixture(c,s);m=guest.Oracle(ws,initial,c,s).run();self.assertEqual((guest.public(m.memory),m.calls,m.snapshots),guest.reference(initial,c,s))
        fired=delays=0
        for c in selected:
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for ws in(self.truth,self.raw):
                    m=guest.Oracle(ws,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                a,b=pair;self.assertEqual((a.r,a.f,a.hi,a.lo,a.memory,a.calls,a.trace,a.current_pc,a.delay_of,a.dispatched_word),(b.r,b.f,b.hi,b.lo,b.memory,b.calls,b.trace,b.current_pc,b.delay_of,b.dispatched_word));fired+=1;delays+=a.delay_of is not None
        self.receipt('rebases-aliases-faults',dict(GNU_links=6,rebase_cases_per_body=n,guest_alias_cases_per_body=40,fired_fault_pairs=fired,delay_slot_cuts=delays,portable_C_alias_or_fault_claim=False))
    def test_04_complete_original_callers(self):
        self.receipt('callers',caller_checks(self))
    def test_05_original_helper_connections(self):
        self.receipt('connections',connection_checks(self))
    def test_06_compiled_semantic_negative_controls(self):
        rows={};cases=list(guest.cases())
        for name,fragment in controls().items():
            obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+fragment,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);witness=None
            for c in cases:
                initial=guest.fixture(c);expected=guest.reference(initial,c)
                m=guest.Oracle(ws,initial,c).run();bad=(guest.public(m.memory),m.calls,m.snapshots)!=expected
                if bad:witness=c;break
            self.assertIsNotNone(witness,name);rows[name]=dict(compiled=True,public_counterexample=vars(witness))
        self.receipt('compiled-controls',rows)
    def test_07_native32_state_calls_and_negative_controls(self):
        text,n=native_program();p=self.out/'native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
        self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],compiled_controls=len(controls()),all_controls_effective=True,pointer32=True,all_14_named_scalars_and_array_elements=True,every_provider_snapshot=True,UBSan_traps=True,artificial_aliases_and_private_stack_mutations_excluded=True))

def native_program():
    chosen=list(dict.fromkeys(c for c in guest.cases()if not c.phase));rows=[]
    arr=lambda values:'{'+','.join('0x%Xu'%guest.u32(v)for v in values)+'}'
    for c in chosen:
        initial=guest.fixture(c);after,calls,snaps=guest.reference(initial,c);kinds=[('func_1501E1B4','func_151F2CDC','func_15080228').index(next(n for n in guest.S if guest.S[n]==t))+1 for t,args in calls];args=[a[0]if a else 0 for t,a in calls];snap=[v for m in snaps for v in guest.observation(m)]
        rows.append('{'+','.join((str(c.slot),str(c.mutation),str(c.poll)+'U',arr(guest.observation(initial)),arr(guest.observation(after)),str(len(calls)),arr(kinds+[0]*(3-len(kinds))),arr(args+[0]*(3-len(args))),arr(snap+[0]*(42-len(snap)))))+'}')
    text=match.HEADER+r'''
u8 D_800C3A58,D_800C35EA[2],D_800BEAC0,D_800C35C0[2];
s32 D_800C35B0[2],D_800C35B8[2],D_800C3640[2],D_800BEA08;s16 D_800C3C8E;
typedef struct {u32 slot,mutation,poll,before[14],after[14],calls,kinds[3],args[3],snapshots[42];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static const Row *current;static u32 calls,bad;
static void observe(u32 *p){p[0]=D_800C3A58;p[1]=(u32)D_800C35B0[0];p[2]=(u32)D_800C35B0[1];p[3]=(u32)D_800C35B8[0];p[4]=(u32)D_800C35B8[1];p[5]=D_800C35EA[0];p[6]=D_800C35EA[1];p[7]=D_800BEAC0;p[8]=(u32)D_800BEA08;p[9]=D_800C35C0[0];p[10]=D_800C35C0[1];p[11]=(u16)D_800C3C8E;p[12]=(u32)D_800C3640[0];p[13]=(u32)D_800C3640[1];}
static int equal(const u32 *p){u32 actual[14],i;observe(actual);for(i=0;i<14;i++)if(actual[i]!=p[i])return 0;return 1;}
static void provider(u32 kind,u32 arg){u32 slot=current->slot,mode=current->mutation;
if(calls>=3){bad=1;return;}if(kind!=current->kinds[calls]||arg!=current->args[calls]||!equal(current->snapshots+calls*14))bad=1;calls++;
if(mode==1&&kind==1)D_800C35B0[slot]=(u32)D_800C35B0[slot]+17U;
if(mode==2&&kind==1){D_800C35B8[slot]=(u16)D_800C3C8E;D_800C35B0[slot]=(u16)D_800C3C8E+1;D_800C35C0[slot]=0;}
if(mode==3&&kind==1){D_800BEAC0=current->before[7]^1;D_800BEA08=(s32)0xFFFFFFF1U;}
if(mode==4&&kind==2){D_800C3640[slot]=(s32)0x80000000U;D_800C35B0[slot]=0x7FFFFFFF;}
if(mode==5&&kind==3){D_800C3640[slot]=0x7FFFFFFF;D_800C35B0[slot]=(s32)0x80000000U;}
if(mode==6&&kind==1){D_800C35EA[slot]=0;D_800C3C8E=(s16)0xFFFF;}
if(mode==7&&kind==3){D_800C35B0[slot]=9;D_800C3640[slot]=9;}}
s32 func_1501E1B4(s32 slot){provider(1,(u32)slot);return (s32)0x81234560U;}
s32 func_151F2CDC(void){provider(2,0);return (s32)current->poll;}
void func_15080228(void){provider(3,0);}
'''
    functions=dict(selected=match.SELECTED,**controls())
    for name,body in functions.items():text+=body.replace(match.FUNCTION,name,1)+'\n'
    text+=r'''
static int check(void(*fn)(s32),const Row *r){const u32*p=r->before;current=r;calls=bad=0;
D_800C3A58=p[0];D_800C35B0[0]=(s32)p[1];D_800C35B0[1]=(s32)p[2];D_800C35B8[0]=(s32)p[3];D_800C35B8[1]=(s32)p[4];D_800C35EA[0]=p[5];D_800C35EA[1]=p[6];D_800BEAC0=p[7];D_800BEA08=(s32)p[8];D_800C35C0[0]=p[9];D_800C35C0[1]=p[10];D_800C3C8E=(s16)p[11];D_800C3640[0]=(s32)p[12];D_800C3640[1]=(s32)p[13];
fn((s32)r->slot);return !bad&&calls==r->calls&&equal(r->after);}
static int run(void){u32 i,j,killed['''+str(len(functions))+r''']={0};void(*functions[])(s32)={'''+','.join(functions)+r'''};
if(sizeof(void*)!=4||sizeof(s32)!=4)return 90;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
    return text,len(chosen)

def caller_checks(test):
    helpers={guest.S[n]for n in('func_1501E1B4','func_151F2CDC','func_15080228')}
    class FrameClock(frame.FrameOracle):
        def record_call(self,t):
            if t in helpers:
                argc=1 if t==guest.S['func_1501E1B4']else 0;self.inner.append((t,tuple(map(guest.u32,self.arguments(argc)))));self.inner_snaps.append(guest.public(self.memory))
            else:super().record_call(t)
        def hook(self,t):
            if t in helpers:provider(self,self.clock_case,t)
            else:super().hook(t)
    class CatchupClock(catchup.Oracle):
        def record_call(self,t):
            if t in helpers:
                argc=1 if t==guest.S['func_1501E1B4']else 0;self.inner.append((t,tuple(map(guest.u32,self.arguments(argc)))));self.inner_snaps.append(guest.public(self.memory))
            else:super().record_call(t)
        def hook(self,t):
            if t in helpers:provider(self,self.clock_case,t)
            else:super().hook(t)
    selected=[guest.Case(),guest.Case(active=0,count=255),guest.Case(mutation=3,paused=1),guest.Case(mutation=4,poll=1),guest.Case(mutation=5,poll=1),guest.Case(marker=65535,time=65535)]
    original_frame=list(struct.unpack_from('>185I',test.rom,0x465E0));original_catchup=list(struct.unpack_from('>66I',test.rom,0x4B7A8));frame_n=catchup_n=0
    for c,phase,mode in itertools.product(selected,(0,8),(0,1)):
        c=replace(c,phase=phase);initial=frame.fixture(count=-1 if phase else 1,pattern=mode,disabled=c.paused);initial.update(guest.public(guest.fixture(c)));expected_inner=[];expected_snaps=[];prior=frame.effects
        def effect(memory,t,args,ordinal,mode):
            if t==match.ENTRY:
                after,inner,snaps=guest.reference(memory,c);memory.update(after);expected_inner.extend(inner);expected_snaps.extend(snaps)
            return prior(memory,t,args,ordinal,mode)
        with patch.object(frame,'effects',effect):expected,calls,actions=frame.reference(initial,mode,phase)
        for ws in(test.truth,test.raw):
            m=FrameClock(original_frame,initial,mode=mode,phase=phase,connected=code(ws));m.clock_case=c;m.inner=[];m.inner_snaps=[];m.run()
            test.assertEqual((guest.public(m.memory),m.calls,m.inner,m.inner_snaps,m.r[2]),(guest.public(expected),calls,expected_inner,expected_snaps,1))
        frame_n+=1
    for c,slot,phase in itertools.product(selected,(0,1),(0,8)):
        c=replace(c,time=max(c.time,c.limit),phase=phase);initial=guest.fixture(c);guest.put(initial,0x800C3C8C,0,1);guest.put(initial,guest.S['D_800C35B0']+4,7);guest.put(initial,guest.S['D_800C3640']+4,3);guest.put(initial,guest.S['D_800C35EA']+1,1,1);cc=catchup.Case(slot=slot,mode=1,phase=phase);expected_inner=[];expected_snaps=[];prior=catchup.effect
        def effect(memory,case,s,t,args,counters):
            if t==match.ENTRY:
                after,inner,snaps=guest.reference(memory,c);memory.update(after);expected_inner.extend(inner);expected_snaps.extend(snaps)
            return prior(memory,case,s,t,args,counters)
        with patch.object(catchup,'effect',effect):expected,calls,observations=catchup.reference(initial,cc)
        for ws in(test.truth,test.raw):
            m=CatchupClock(original_catchup,initial,cc,connected=code(ws));m.clock_case=c;m.inner=[];m.inner_snaps=[];m.run()
            test.assertEqual((guest.public(m.memory),m.calls,m.inner,m.inner_snaps),(guest.public(expected),calls,expected_inner,expected_snaps))
        catchup_n+=1
    actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump')
    test.assertEqual(actual['func_15019130'],original_frame);test.assertEqual(actual['func_1501E2F8'],original_catchup)
    return dict(frame185_cases_per_body=frame_n,catchup66_cases_per_body=catchup_n,both_caller_baselines_exact=True,complete_returns_and_provider_snapshots=True,typed_void_interface=True)

def connection_checks(test):
    entries=((0x1501E1B4,0x4B664,81),(0x151F2CDC,0x22018C,36),(0x15080228,0xAD6D8,72));connected={};visited=set();cases=0
    for entry,offset,n in entries:connected.update(code(list(struct.unpack_from('>%dI'%n,test.rom,offset)),entry))
    mask,queue=0x10024880,0x100126E8
    class Connected(guest.Oracle):
        def record_call(self,t):
            if t in(mask,queue):self.nested.append((t,tuple(map(guest.u32,self.arguments(1 if t==mask else 2)))))
            else:super().record_call(t)
        def hook(self,t):
            test.assertIn(t,(mask,queue))
            if t==queue:test.assertEqual(self.nested[-1][1],(guest.u32(self.r[29]+56),256))
            else:test.assertEqual(self.nested[-1][1],(1,)if len([x for x in self.nested if x[0]==mask])==1 else(0x12345678,))
            for i in range(4):self.put(guest.u32(self.r[29]+4*i),0xB5000000+i,4)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x12345678 if t==mask else 0
    for backend,slot,phase in itertools.product((0,1,2,3,5,6,7,0xFFFFFFFF),(0,1),(0,8)):
        c=guest.Case(slot=slot,phase=phase,poll=backend if backend in(1,2,5,6,7)else 0);initial=guest.fixture(c);guest.put(initial,0x800C3C88,2,1);guest.put(initial,0x800E0E04,backend)
        expected=guest.reference(initial,c)
        for ws in(test.truth,test.raw):
            m=Connected(ws,initial,c,connected=connected);m.nested=[];m.run();test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),expected);visited.update(m.visits)
            test.assertEqual([t for t,a in m.nested],[mask,mask]+([queue]if backend==1 else[]))
        cases+=1
    actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump');baseline={}
    for entry,offset,n in entries:
        name='func_%08X'%entry;truth=list(struct.unpack_from('>%dI'%n,test.rom,offset));baseline[name]=dict(slot_words=n,baseline_exact=actual[name]==truth,visited_words=sum(entry<=a<entry+n*4 for a in visited))
    test.assertFalse(baseline['func_1501E1B4']['baseline_exact']);test.assertTrue(baseline['func_151F2CDC']['baseline_exact']);test.assertTrue(baseline['func_15080228']['baseline_exact'])
    return dict(cases_per_body=cases,helpers=baseline,gate_helper_state2_only=True,original_audio_flag_getter=True,command_queue_empty_only=True,OS_mask_and_queue_providers_bounded=True,gate_helper_not_credited=True)

if __name__=='__main__':unittest.main()
