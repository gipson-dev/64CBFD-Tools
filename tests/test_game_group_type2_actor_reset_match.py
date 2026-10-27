"""Direct actor reset: byte selector ABI, live gates, caller chain and strict image."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct,subprocess,time,unittest
from tools.experiments import game_group_type2_actor_reset_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
LIVE,RECORDS,FLAGS,ROW,ACTOR,POOL=0x800C35C8,0x800C35F0,0x20000,0x30000,0x50000,0x800CC2D0
GATE,COUNT,BUSY,PRE=0x800C35EA,0x800C363A,0x800C3638,0x15022398
BYTES=(0x6C,0x6D,0x6A,0x6B);HALVES=(0x282,0x27A,0x27C,0x27E,0x280)
@dataclass(frozen=True)
class Case:
    index:int=0
    group:int=0
    active:int=1
    kind:int=2
    selector:int=255
    present:bool=True
    mutate:bool=False
    phase:int=0
    alias:int=0
    actor_at:int=0

def record_address(c):return ROW+c.group*64+c.index*8

def actor_address(c):return c.actor_at or (record_address(c)if c.alias==1 else STACK+c.phase-0x100 if c.alias==2 else ACTOR)

def fixture(c):
    m={}
    for base,size in((LIVE,8),(RECORDS,8),(FLAGS,64),(ROW,128),(ACTOR,0x300),(STACK+c.phase-0x400,0x800)):
        m.update({base+i:(i*13+0x5A)&255 for i in range(size)})
    actor=actor_address(c)
    for i in range(0x300):m[actor+i]=(i*13+0x5A)&255
    for g in range(2):put(m,LIVE+4*g,FLAGS+g*16);put(m,RECORDS+4*g,ROW+g*64)
    put(m,FLAGS+c.group*16+c.index*2,c.active,2);record=record_address(c);put(m,record,c.kind,2);m[record+2]=c.selector
    assert c.alias==2 or not STACK-0x400<=actor<STACK+0x400
    assert all(actor+i in m for i in range(0x300))
    return m

def clobber(m,sp):
    for i in range(4):put(m,sp+i*4,0xB5000000+i)

def effect(m,c,reset=False,record=None):
    record=record_address(c)if record is None else record
    if c.mutate:
        put(m,record,3,2);m[record+2]^=255
        # Both pointer tables may change after the initial record selection.
        put(m,LIVE+c.group*4,0xBAD00000);put(m,RECORDS+c.group*4,0xBAD10000)
    if reset:m[actor_address(c)+0x71]=0x7D

def reference(initial,c):
    m=dict(initial);calls=[];flag=(read(m,LIVE+c.group*4)+((c.index*2)&0xFFFFFFFF))&0xFFFFFFFF
    if read(m,flag,2):
        record=(read(m,RECORDS+c.group*4)+((c.index*8)&0xFFFFFFFF))&0xFFFFFFFF
        if read(m,record,2)==2:
            calls.append((source.LOOKUP,(m[record+2],)));effect(m,c,record=record)
            if c.present:
                a=actor_address(c)
                for at in BYTES:m[a+at]=0
                for at in HALVES:put(m,a+at,0,2)
                calls.append((source.RESET,(a,0,3,65535,10)));effect(m,c,True,record);m[a+0x71]=0
    return m,calls

def public(m):return {a:b for a,b in m.items()if not STACK-0x400<=a<STACK+0x400}

class ResetOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,symbols=None,before_mode=0):
        self.case=c;self.last_target=c;self.before_mode=before_mode
        self.provider_symbols=symbols or dict(lookup=source.LOOKUP,reset=source.RESET)
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=arguments or(c.index,c.group),connected=connected)
    def record_call(self,target):
        if target==source.ENTRY:
            index,group=self.arguments(2);self.last_target=replace(self.case,index=index,group=group,mutate=False)
        sizes={source.ENTRY:2,PRE:2,self.provider_symbols['lookup']:1,self.provider_symbols['reset']:5}
        assert target in sizes,hex(target)
        args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        c=self.last_target;record=record_address(c)
        if target==PRE:
            i,g=self.arguments(2)
            if i==0 and self.before_mode: self.memory[COUNT+g]=1 if self.before_mode==1 else 3
            if self.before_mode==3:put(self.memory,FLAGS+g*16+i*2,0,2)
        elif target==self.provider_symbols['lookup']:effect(self.memory,c,record=record)
        elif target==self.provider_symbols['reset']:
            self.assert_reset(c);effect(self.memory,c,True,record)
        else:raise AssertionError(hex(target))
        clobber(self.memory,self.r[29])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=actor_address(c)if target==self.provider_symbols['lookup']and c.present else 0 if target==self.provider_symbols['lookup']else 0xDEADBEEF
    def assert_reset(self,c):
        a=actor_address(c)
        assert self.calls[-1][1]==(a,0,3,65535,10),self.calls[-1]
        assert all(self.memory[a+i]==0 for i in BYTES)
        assert all(read(self.memory,a+i,2)==0 for i in HALVES)

def controls():
    b=source.SELECTED
    result=dict(active_gate=b.replace('== 0','!= 0',1),type_gate=b.replace('!= 2','!= 3'),stride=b.replace('* 8','* 4'),
        selector=b.replace('record[2]','(record[2] & 0x7F)'),missing_byte=b.replace('actor[0x6D] = 0;','actor[0x6D] = 1;'),
        missing_half=b.replace('actor + 0x282','actor + 0x284'),channel=b.replace('actor, 0, 3','actor, 1, 3'),
        duration=b.replace('0xFFFF','0x7FFF'),amount=b.replace('0xFFFF, 10','0xFFFF, 11'),
        final_byte=b.replace('        actor[0x71] = 0;',''),
        early_final=b.replace('        func_1507E7E4(actor, 0, 3, 0xFFFF, 10);\n        actor[0x71] = 0;',
                              '        actor[0x71] = 0;\n        func_1507E7E4(actor, 0, 3, 0xFFFF, 10);'))
    assert all(v!=b for v in result.values())
    return result

def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
u16 *D_800C35C8[2];u8 *D_800C35F0[2];
typedef void(*Reset)(s32,s32);
static u8 *arena,*expected,*actor,*record;
static u32 error,lookups,resets,identity,present,mutate;
typedef char ABI[(sizeof(void*)==4&&sizeof(u8)==1&&sizeof(u16)==2&&sizeof(s32)==4)?1:-1];
__attribute__((noinline,noclone)) u8 *func_15083E90(u8 selector){
 if(selector!=identity||lookups++)error=1;
 if(mutate){*(u16*)(void*)record=3;record[2]^=255;}
 return present?actor:0;
}
__attribute__((noinline,noclone)) void func_1507E7E4(u8*p,u8 channel,u8 priority,u16 duration,s32 amount){
 u32 i;const u32 bytes[]={0x6C,0x6D,0x6A,0x6B},halves[]={0x282,0x27A,0x27C,0x27E,0x280};
 if(p!=actor||channel||priority!=3||duration!=65535||amount!=10||resets++)error=1;
 for(i=0;i<4;i++)if(p[bytes[i]])error=1;
 for(i=0;i<5;i++)if(*(u16*)(void*)(p+halves[i]))error=1;
 p[0x71]=0x7D;
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''
static int one(Reset fn,u32 index,u32 group,u32 active,u32 kind,u32 id,u32 found,u32 mutation,u32 alias){
 u32 i,offset,invoke,byteOffsets[]={0x6C,0x6D,0x6A,0x6B},halfOffsets[]={0x282,0x27A,0x27C,0x27E,0x280};
 for(i=0;i<0x800;i++)arena[i]=(u8)(i*13+0x5A);
 for(i=0;i<2;i++){D_800C35C8[i]=(u16*)(void*)(arena+0x100+i*16);D_800C35F0[i]=arena+0x200+i*64;}
 record=D_800C35F0[group]+index*8;actor=alias?record:arena+0x400;
 D_800C35C8[group][index]=(u16)active;*(u16*)(void*)record=(u16)kind;record[2]=(u8)id;
 for(i=0;i<0x800;i++)expected[i]=arena[i];offset=(u32)(actor-arena);
 invoke=active&&kind==2;identity=(u8)id;present=found;mutate=mutation;error=lookups=resets=0;
 if(invoke&&mutation){*(u16*)(void*)(expected+(record-arena))=3;expected[record-arena+2]^=255;}
 if(invoke&&found){for(i=0;i<4;i++)expected[offset+byteOffsets[i]]=0;
 for(i=0;i<5;i++)*(u16*)(void*)(expected+offset+halfOffsets[i])=0;expected[offset+0x71]=0;}
 fn((s32)index,(s32)group);
 if(error||lookups!=invoke||resets!=(invoke&&found))return 23;
 for(i=0;i<0x800;i++)if(arena[i]!=expected[i])return 23;return 0;
}
static int variant(Reset fn,u32 full){u32 id,g,i,a,k,p,m,x;
 for(id=0;id<(full?256u:4u);id++)for(g=0;g<2;g++)for(i=0;i<2;i++)for(a=0;a<2;a++)for(k=0;k<3;k++)
 for(p=0;p<2;p++)for(m=0;m<2;m++)for(x=0;x<2;x++)
 if(one(fn,i*3,g,a?65535:0,(u32[]){1,2,65535}[k],full?id:(u32[]){0,127,128,255}[id],p,m,x))return 23;return 0;
}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u8 *(*lookup)(u8)=func_15083E90;void(*reset)(u8*,u8,u8,u16,s32)=func_1507E7E4;
 if(!lookup||!reset)return 97;arena=allocate(0x1000);if(!arena)return 97;expected=arena+0x800;
 if(variant(selected,1))return 1;
'''
    for i,name in enumerate(controls(),2):text+=' if(!variant('+name+',0))return '+str(i)+';\n'
    return text+' return 0;}\n'+START

class GroupType2ActorResetTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out)
        cls.fresh=cls.out/('fresh-run-'+str(os.getpid())+'-'+str(time.time_ns()));cls.fresh.mkdir()
        cls.obj,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.DECLARATIONS+'\n'+source.SELECTED+'\n','fresh-selected')
        if diag:raise ValueError(diag)
        source.checked_payload(*source.payload(cls.obj));data,fs=source.link_owner(ROOT,cls.fresh,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
        rom=cls.values['conker/conker.us.bin'];old=cls.values['conker/build/conker.us.elf']
        cls.truth=list(struct.unpack_from('>46I',rom,source.ROM));cls.parent=list(struct.unpack_from('>39I',rom,source.PARENT_ROM))
        cls.lookup=list(struct.unpack_from('>72I',rom,source.LOOKUP_ROM))
        cls.retained_parent=list(struct.unpack_from('>39I',old,source.elf_slot_offset(old,source.PARENT,156)))
        cls.retained_lookup=list(struct.unpack_from('>72I',old,source.elf_slot_offset(old,source.LOOKUP,288)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),initial=None,images=None,entry=source.ENTRY,symbols=None,connected=None):
        initial=fixture(c)if initial is None else initial;expected,calls=reference(initial,c);pair=[]
        for words in images or(self.truth,self.words):
            x=ResetOracle(words,initial,c,entry,connected,symbols=symbols).run()
            normal=[(source.LOOKUP if symbols and t==symbols['lookup']else source.RESET if symbols and t==symbols['reset']else t,a)for t,a in x.calls]
            self.assertEqual(normal,calls,c);self.assertEqual(public(x.memory),public(expected),c);pair.append(x)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_Make_callsite_and_actual_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.retained_parent);self.assertEqual(self.lookup,self.retained_lookup)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label,text in(('before',self.values[source.SOURCE].decode()),('after',(self.out/'proposed-owner.c').read_text())):
            obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-owner-'+label);self.assertFalse(diag)
            self.assertEqual(source.same_functions(obj,self.out/(('before'if label=='before'else'after')+'-owner.o')),57)
            if label=='after':self.assertEqual(source.payload(obj),source.payload(self.obj))
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),56)
        self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_49D30.c.o.compact'),57)
        for text in(self.values['conker/src/game/generated_AEB40.c'].decode(),):self.assertIn('u8 *func_15083E90(u8 selector)',text)
        self.assertIn('void func_1507E7E4(u8 *actor, u8 channel, u8 priority, u16 duration, s32 amount)',self.values['conker/src/game/generated_AB760.c'].decode())
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        direct=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==jal]
        literals=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
        self.assertEqual((direct,literals),([0x4FD54],[]))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,12)
        c=Case();initial=fixture(c);stub=ResetOracle(struct.unpack_from('>3I',old,at),initial,c).run()
        self.assertNotEqual(public(stub.memory),public(reference(initial,c)[0]))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=40,guards=0,bindings=6,neighbors=56,compact_functions_equal=57,
            actual_Make_commands=3,no_unroll_profile=True,target_and_owner_diagnostics_empty=True,canonical_ABI='void(s32,s32)',
            actual_lookup_ABI='u8*(u8)',actual_reset_ABI='void(u8*,u8,u8,u16,s32)',legacy_shared_header_unchanged=True,direct_sites=direct,literal_sites=literals)
    def test_02_guest_gates_byte_selectors_aliases_and_provider_mutation(self):
        visits=set();count=0
        cases=[Case(index,group,active,kind,selector,present,mutate,phase,alias)
            for index,group,active,kind,selector,present,mutate,phase,alias in itertools.product((0,3),(0,1),(0,1,65535),(0,2,65535),(0,127,128,255),(False,True),(False,True),(0,8),(0,1))]
        cases.extend(Case(selector%4,selector%2,1,2,selector,True,True)for selector in range(256))
        for c in cases:
            x=self.compare(c);visits.update(x.visits);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4)))
        self.receipt['guest']=dict(cases=count,all_selector_bytes=True,all_46_words_visited=True,full_private_state_equal=True,
            public_actor_0x300_bytes_observable=True,native_valid_and_record_aliases=True,provider_clobbers=True,pointer_and_record_mutations_after_lookup=True)
    def test_03_actual_72_word_lookup_connected(self):
        visits=set();count=0
        for selector,hit,inactive_first,phase in itertools.product((0,1,127,128,255),tuple(range(-1,26)),(False,True),(0,8)):
            present=selector!=0 and hit>=0;c=Case(selector=selector,present=present,phase=phase,actor_at=POOL+max(hit,0)*0x32C)
            initial=fixture(c)
            for i in range(26*0x32C):initial[POOL+i]=(i*17+0xA5)&255
            for i in range(26):put(initial,POOL+i*0x32C,0 if inactive_first else 1);initial[POOL+i*0x32C+0x3B]=selector if inactive_first else (selector+1)&255
            if present:
                put(initial,POOL+hit*0x32C,1);initial[POOL+hit*0x32C+0x3B]=selector
                if hit<25:put(initial,POOL+(hit+1)*0x32C,1);initial[POOL+(hit+1)*0x32C+0x3B]=selector
                if inactive_first and hit>0:put(initial,POOL,0);initial[POOL+0x3B]=selector
            pair=[];expected,_=reference(initial,c)
            for provider in(self.lookup,self.retained_lookup):
                for words in(self.truth,self.words):
                    connected={source.LOOKUP+i*4:w for i,w in enumerate(provider)}
                    x=ResetOracle(words,initial,c,connected=connected).run();visits.update(x.visits)
                    self.assertEqual(public(x.memory),public(expected),(selector,hit));pair.append(x)
                self.assertEqual(complete(pair[-2]),complete(pair[-1]))
            count+=1
        self.assertTrue(set(range(source.LOOKUP,source.LOOKUP+288,4))-{source.LOOKUP+120,source.LOOKUP+156,source.LOOKUP+192,source.LOOKUP+228}<=visits,sorted(hex(x-source.LOOKUP)for x in set(range(source.LOOKUP,source.LOOKUP+288,4))-visits))
        self.receipt['lookup']=dict(cases=count,original_and_retained_72_words=True,zero_selector_returns_NULL=True,
            first_live_match_of_26=True,high_selector_bytes_unsigned=True,inner_reset_provider_is_bounded_contract=True,no_helper_credit=True)
    def test_04_full_original_and_retained_caller_dynamic_count(self):
        count=0;visits=set()
        for group,gate,length,mode,phase in itertools.product((0,1),(0,1,2,255),(0,1,2,3),range(4),(0,8)):
            c=Case(group=group,phase=phase);initial=fixture(c)
            for g in range(2):initial[GATE+g]=gate;initial[COUNT+g]=length
            initial[BUSY]=0xA5
            for i in range(4):put(initial,FLAGS+group*16+i*2,1,2);put(initial,ROW+group*64+i*8,2,2);initial[ROW+group*64+i*8+2]=128+i
            expected=dict(initial);calls=[]
            if gate==1:
                expected[BUSY]=0;i=0
                while i<expected[COUNT+group]:
                    calls.append((PRE,(i,group)))
                    if i==0 and mode:expected[COUNT+group]=1 if mode==1 else 3
                    if mode==3:put(expected,FLAGS+group*16+i*2,0,2)
                    calls.append((source.ENTRY,(i,group)));expected,tail=reference(expected,replace(c,index=i,mutate=False));calls.extend(tail);i+=1
                expected[BUSY]=1
            for parent in(self.parent,self.retained_parent):
                pair=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                    x=ResetOracle(parent,initial,c,entry=source.PARENT,connected=connected,arguments=(group,),before_mode=mode).run()
                    self.assertEqual(x.calls,calls,(group,gate,length,mode));self.assertEqual(public(x.memory),public(expected));visits.update(x.visits);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.assertTrue(set(range(source.PARENT,source.PARENT+156,4))<=visits)
        self.receipt['caller']=dict(cases=count,all_39_words_visited=True,original_and_retained=True,target_46_words_connected=True,
            count_shrink_and_growth=True,arguments_survive_predecessor_clobbers=True,predecessor_is_placeholder_bounded_contract=True,whole_gameplay_claimed=False)
    def test_05_native32_actual_C_and_effective_controls(self):
        text=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            p.with_suffix('.diagnostics.txt').write_text(result.stdout+result.stderr);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=256*2*2*2*3*2*2*2,effective_controls=len(controls()),
            all_byte_selectors=True,heap_backed_typeless_fixture=True,trap_UBSan=True,typed_function_pointer_interfaces=True,valid_array_domains_only=True)
    def test_06_fault_prefixes_sparse_lazy_reads_and_guest_stack_alias(self):
        count=0
        for c in(Case(active=0),Case(kind=1),Case(present=False),Case(),Case(mutate=True,alias=1)):
            x=self.compare(c);initial=fixture(c)
            for fault in range(x.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=ResetOracle(words,initial,c);m.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,fault);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        sparse=[]
        c=Case(active=0);m=fixture(c);sparse.append((c,{a:b for a,b in m.items()if STACK-0x400<=a<STACK+0x400 or LIVE<=a<LIVE+8 or FLAGS<=a<FLAGS+64}))
        c=Case(kind=1);m=fixture(c);sparse.append((c,{a:b for a,b in m.items()if not ACTOR<=a<ACTOR+0x300}))
        for c,initial in sparse:self.compare(c,initial)
        bad=source.SELECTED.replace('    u8 *record;','    u8 *record;\n    (void)*(volatile u32 *)D_800C35F0[group];')
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+bad,'negative-hoisted-read');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        with self.assertRaisesRegex(AssertionError,'unmapped read'):ResetOracle(words,sparse[0][1],sparse[0][0]).run()
        for phase,mutate in itertools.product((0,8),(False,True)):
            c=Case(phase=phase,mutate=mutate,alias=2);initial=fixture(c)
            pair=[ResetOracle(w,initial,c).run()for w in(self.truth,self.words)];self.assertEqual(complete(pair[0]),complete(pair[1]))
        self.receipt['faults']=dict(fired_prefix_pairs=count,sparse_lazy_gates=2,compiled_early_read_negative=True,guest_only_stack_alias_cases=4,hardware_timing_claimed=False)
    def test_07_actual_padder_and_GNU_rebases_no_guards(self):
        raw,bindings=source.checked_payload(*source.payload(self.obj))
        for data,rels in((raw[:-4],bindings),(bytes([raw[0]^1])+raw[1:],bindings),(raw,dict(bindings,**{} )|{12:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(data,rels)
        padded=self.fresh/'fresh-padded.s';padded.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER))
        obj=padded.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
        self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        anchors=dict(D_800C35C8=LIVE,D_800C35F0=RECORDS,func_15083E90=source.LOOKUP,func_1507E7E4=source.RESET)
        asm,missing=emit_function(raw,dict(value=0,size=184),bindings,source.FUNCTION,anchors);self.assertFalse(missing)
        p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        count=0
        for layout,(entry,live,records,lookup,reset)in enumerate(((source.ENTRY,LIVE,RECORDS,source.LOOKUP,source.RESET),(0x152222E0,0x81207FF8,0x81208000,0x15383E90,0x1537E7E4),(0x154222E0,0x8120FFF8,0x81210000,0x15783E90,0x1577E7E4))):
            anchors=dict(D_800C35C8=live,D_800C35F0=records,func_15083E90=lookup,func_1507E7E4=reset);images=[]
            for j,object_ in enumerate((self.out/'original-func_150222E0.o',obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(layout,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in anchors.items()],'-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for selector,active,kind,present in itertools.product((0,128,255),(0,1),(1,2),(False,True)):
                c=Case(selector=selector,active=active,kind=kind,present=present);initial=fixture(c)
                for old,new in((LIVE,live),(RECORDS,records)):
                    for offset in range(8):initial[new+offset]=initial[old+offset]
                self.compare(c,initial,images,entry,dict(lookup=lookup,reset=reset));count+=1
        self.receipt['rebases']=dict(layouts=3,GNU_links=6,guest_cases=count,HI16_LO16_carry=True,all_6_bindings=True,guards=0,negative_raw_checks=3)
    def test_08_strict_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out)
        before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184]
        expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos+8 for pos,name,f,_ in source.symbol_rows(before)if name==source.FUNCTION and f[1:3]==(source.ENTRY,12))
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(150,149,1,0))
        self.receipt['strict']=dict(changed_bytes=150,code_bytes=149,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(values),guard_manifest_unchanged=True)

if __name__=='__main__':unittest.main()
