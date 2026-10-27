"""Actor transition start: signed pool indexing, callback lifetimes and retail dispatch."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct,subprocess,time,unittest
from tools.experiments import game_actor_transition_start_match as source
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
POOL,NEST1,NEST2,PACKET=0x800CC2D0,0x51000,0x52000,0x60000
BUSY,VALID=0x800C3638,0x800C3654
@dataclass(frozen=True)
class Case:
    slot:int=0
    offset:int=0
    mutate:int=0
    alias:int=0
    phase:int=0
    actor_at:int=0

def actor_address(c,pool=POOL):return c.actor_at or((pool+c.slot*0x32C+c.offset)&0xFFFFFFFF)
def entry_address(c,pool=POOL):
    delta=(actor_address(c,pool)-pool)&0xFFFFFFFF;delta=delta if delta<0x80000000 else delta-0x100000000
    index=(abs(delta)//0x32C)*(-1 if delta<0 else 1)
    return(pool+index*0x32C)&0xFFFFFFFF

def nested_address(c,pool=POOL):
    a,e=actor_address(c,pool),entry_address(c,pool)
    return(a+0xB if c.alias==1 else a+0x11 if c.alias==2 else e+0x2A4 if c.alias==3 else NEST1)&0xFFFFFFFF

def fixture(c,pool=POOL):
    a,e,n=actor_address(c,pool),entry_address(c,pool),nested_address(c,pool);m={}
    areas=[(STACK+c.phase-0x500,0xA00),(a-16,0x360),(e-16,0x360),(n-16,0x420),(NEST2-16,0x420)]
    if c.alias==3:areas.append((((n&0xFFFFFF)|0x3B000000)-16,0x420))
    for base,size in areas:
        for i in range(size):m[(base+i)&0xFFFFFFFF]=(i*13+0x5A)&255
    put(m,e+0x31C,n);return m

def effect(m,c,target,pool=POOL):
    a,n=actor_address(c,pool),nested_address(c,pool)
    if target==source.SPAWN:
        if c.mutate&1:
            for at,value in((0x8A,0xE7),(0x89,0xC3),(0x83,0xB1)):m[a+at]=value
            put(m,a+0x90,0x87654321)
        if c.mutate&2:put(m,a+0x31C,NEST2);m[n+0x11A]=0xC1
    elif target==source.ANIMATE:
        if c.mutate&1:
            for at,value in((0x8A,0x6D),(0x89,0x71),(0x83,0x93)):m[a+at]=value
        if c.mutate&2:put(m,a+0x94,0xCAFEBABE)

def reference(initial,c,pool=POOL,quiet_animate=False):
    m=dict(initial);a,e=actor_address(c,pool),entry_address(c,pool)
    n=read(m,e+0x31C);m[n+0x78]=0x3B;n=read(m,e+0x31C);m[n+0x11A]=2
    calls=[(source.SPAWN,(a,0x89,0x3F800000,0))];effect(m,c,source.SPAWN,pool)
    m[a+0x8A]=20;m[a+0x89]=0;m[a+0x83]=0
    calls.append((source.ANIMATE,(a,0x221,0x3F800000,0,0,0,0)))
    if not quiet_animate:effect(m,c,source.ANIMATE,pool)
    return m,calls

def public(m):return {a:b for a,b in m.items()if not STACK-0x500<=a<STACK+0x500}

class TransitionOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,pool=POOL,symbols=None,found=True):
        self.case,self.pool,self.found=c,pool,found
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=arguments or(actor_address(c,pool),),connected=connected)
        self.providers=symbols or dict(spawn=source.SPAWN,animate=source.ANIMATE)
    def record_call(self,target):
        sizes={self.providers['spawn']:4,self.providers['animate']:7,source.GET_ACTOR:1,source.ENTRY:1,source.OTHER:1}
        assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        a,e=actor_address(self.case,self.pool),entry_address(self.case,self.pool)
        if target==self.providers['spawn']:
            assert args==(a,0x89,0x3F800000,0),args
            assert self.memory[nested_address(self.case,self.pool)+0x78]==0x3B,'nested byte before spawn'
            assert self.memory[read(self.memory,e+0x31C)+0x11A]==2,'nested state before spawn'
        if target==self.providers['animate']:
            assert args==(a,0x221,0x3F800000,0,0,0,0),args
            assert(self.memory[a+0x8A],self.memory[a+0x89],self.memory[a+0x83])==(20,0,0)
    def hook(self,target):
        c=self.case
        if target==self.providers['spawn']:effect(self.memory,c,source.SPAWN,self.pool)
        elif target==self.providers['animate']:effect(self.memory,c,source.ANIMATE,self.pool)
        elif target not in(source.GET_ACTOR,source.OTHER):raise AssertionError(hex(target))
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=(actor_address(c,self.pool)if self.found else 0)if target==source.GET_ACTOR else NEST2 if target==self.providers['spawn']else 0xDEADBEEF

def controls():
    b=source.SELECTED;clears='    actor->disable_jump = 20;\n    actor->disable_run = 0;\n    actor->unk83 = 0;\n'
    first='    func_15083568((u8 *)actor, 0x89, 1.0f, 0);\n'
    last='    func_1505E650((u8 *)actor, 0x221, 1.0f, 0.0f, 0.0f, 0.0f, 0);'
    result=dict(nested_byte=b.replace('unk78 = 0x3B','unk78 = 0x3A'),nested_state=b.replace('unk11A = 2','unk11A = 3'),
        first_state=b.replace('0x89, 1.0f','0x88, 1.0f'),first_scale=b.replace('0x89, 1.0f','0x89, 0.5f'),first_mode=b.replace('0x89, 1.0f, 0','0x89, 1.0f, 1'),
        jump=b.replace('disable_jump = 20','disable_jump = 21'),run_flag=b.replace('disable_run = 0','disable_run = 1'),byte83=b.replace('unk83 = 0','unk83 = 1'),
        last_state=b.replace('0x221','0x220'),last_scale=b.replace('0x221, 1.0f','0x221, 0.5f'),last_mode=b.replace('0.0f, 0);','0.0f, 1);'),
        early_clears=b.replace(first+clears,clears+first),late_clears=b.replace(clears,'').replace(last,last+'\n'+clears.rstrip()),
        use_return=b.replace(first,'    actor = (struct127 *)func_15083568((u8 *)actor, 0x89, 1.0f, 0);\n'))
    assert all(v!=b for v in result.values()),[n for n,v in result.items()if v==b]
    return result

def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
struct127 D_800CC2D0[26];
typedef void(*Transition)(struct127*);
static u8 *n1,*n2,*expected,*actorBytes;static struct127 *current;
static u32 error,spawns,animations,mutation;static u8 *initialNested;
typedef char ABI[(sizeof(void*)==4&&sizeof(struct127)==0x32C&&sizeof(struct126)<=0x400&&
 __builtin_offsetof(struct127,unk31C)==0x31C&&__builtin_offsetof(struct127,disable_jump)==0x8A&&
 __builtin_offsetof(struct127,disable_run)==0x89&&__builtin_offsetof(struct127,unk83)==0x83&&
 __builtin_offsetof(struct126,unk78)==0x78&&__builtin_offsetof(struct126,unk11A)==0x11A)?1:-1];
__attribute__((noinline,noclone)) u8 *func_15083568(u8*p,s32 animation,f32 scale,s32 mode){
 if(p!=(u8*)current||animation!=0x89||scale!=1.0f||mode||spawns++)error=1;
 if(initialNested[0x78]!=0x3B||initialNested[0x11A]!=2)error=1;
 if(mutation&1){p[0x8A]=0xE7;p[0x89]=0xC3;p[0x83]=0xB1;*(u32*)(void*)(p+0x90)=0x87654321;}
 if(mutation&2){current->unk31C=(struct126*)(void*)n2;initialNested[0x11A]=0xC1;}
 return n2;
}
__attribute__((noinline,noclone)) void func_1505E650(u8*p,u16 animation,f32 scale,f32 a,f32 b,f32 c,s32 mode){
 if(p!=(u8*)current||animation!=0x221||scale!=1.0f||a!=0.0f||b!=0.0f||c!=0.0f||mode||animations++){error=1;return;}
 if(p[0x8A]!=20||p[0x89]||p[0x83])error=1;
 if(mutation&1){p[0x8A]=0x6D;p[0x89]=0x71;p[0x83]=0x93;}
 if(mutation&2)*(u32*)(void*)(p+0x94)=0xCAFEBABE;
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''
static int one(Transition fn,u32 slot,u32 pattern,u32 mutate,u32 bank){
 u32 i;u8 *ea=expected,*e1=expected+0x400,*e2=expected+0x800;
 current=&D_800CC2D0[slot];actorBytes=(u8*)current;initialNested=bank?n2:n1;
 for(i=0;i<0x32C;i++)actorBytes[i]=(u8)(i*13+pattern);
 for(i=0;i<0x400;i++){n1[i]=(u8)(i*17+pattern);n2[i]=(u8)(i*23+pattern);}
 current->unk31C=(struct126*)(void*)initialNested;
 for(i=0;i<0x32C;i++)ea[i]=actorBytes[i];
 for(i=0;i<0x400;i++){e1[i]=n1[i];e2[i]=n2[i];}
 (bank?e2:e1)[0x78]=0x3B;(bank?e2:e1)[0x11A]=2;
 if(mutate&1){*(u32*)(void*)(ea+0x90)=0x87654321;}
 if(mutate&2){*(struct126**)(void*)(ea+0x31C)=(struct126*)(void*)n2;(bank?e2:e1)[0x11A]=0xC1;}
 ea[0x8A]=20;ea[0x89]=0;ea[0x83]=0;
 if(mutate&1){ea[0x8A]=0x6D;ea[0x89]=0x71;ea[0x83]=0x93;}
 if(mutate&2)*(u32*)(void*)(ea+0x94)=0xCAFEBABE;
 error=spawns=animations=0;mutation=mutate;fn(current);
 if(error||spawns!=1||animations!=1)return 23;
 for(i=0;i<0x32C;i++)if(ea[i]!=actorBytes[i])return 23;
 for(i=0;i<0x400;i++)if(e1[i]!=n1[i]||e2[i]!=n2[i])return 23;return 0;
}
static int variant(Transition fn,u32 full){u32 s,p,m,b;
 for(s=0;s<(full?26u:2u);s++)for(p=0;p<(full?256u:4u);p++)for(m=0;m<4;m++)for(b=0;b<2;b++)
 if(one(fn,full?s:s*25,p,m,b))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u8 *(*spawn)(u8*,s32,f32,s32)=func_15083568;void(*animate)(u8*,u16,f32,f32,f32,f32,s32)=func_1505E650;
 if(!spawn||!animate)return 97;n1=allocate(0x1800);if(!n1)return 97;n2=n1+0x400;expected=n1+0x800;
 if((u32)D_800CC2D0>0x7FFFFFFF)return 97;if(variant(selected,1))return 1;
'''
    for i,name in enumerate(controls(),2):text+=' if(!variant('+name+',0))return '+str(i)+';\n'
    return text+' return 0;}\n'+START

class ActorTransitionStartTests(unittest.TestCase):
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
        rom=cls.values['conker/conker.us.bin'];old=cls.values['conker/build/conker.us.elf'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM))
        cls.parent=list(struct.unpack_from('>2146I',rom,source.PARENT_ROM));cls.table=rom[source.TABLE_ROM:source.TABLE_ROM+568]
        cls.animate=list(struct.unpack_from('>95I',rom,0x8BB00));cls.retained_animate=list(struct.unpack_from('>95I',old,source.elf_slot_offset(old,source.ANIMATE,380)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),initial=None,images=None,entry=source.ENTRY,pool=POOL,symbols=None,connected=None,quiet_animate=False):
        initial=fixture(c,pool)if initial is None else initial;expected,calls=reference(initial,c,pool,quiet_animate);pair=[]
        for words in images or(self.truth,self.words):
            m=TransitionOracle(words,initial,c,entry,connected,pool=pool,symbols=symbols).run()
            normal=[(source.SPAWN if symbols and t==symbols['spawn']else source.ANIMATE if symbols and t==symbols['animate']else t,a)for t,a in m.calls]
            self.assertEqual(normal,calls,c);self.assertEqual(public(m.memory),public(expected),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_actual_Make_and_retail_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.animate,self.retained_animate)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label,text in(('before',self.values[source.SOURCE].decode()),('after',(self.out/'proposed-owner.c').read_text())):
            obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-owner-'+label);self.assertFalse(diag)
            self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),19)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),18)
        self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_90840.c.o.compact'),19)
        cmds=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(cmds),5);self.assertIn('-O2',cmds[1]);self.assertIn('-g3',cmds[1]);self.assertFalse(any('-loopunroll'in x for cmd in cmds for x in cmd))
        self.assertIn('u8 *func_15083568(u8 *actor, s32 animation, f32 scale, s32 mode)',self.values['conker/src/game/generated_AEB40.c'].decode())
        asm=self.values['conker/asm/nonmatchings/game_83300/func_1505E650.s'].decode();self.assertIn('lhu        $a3, 0x4E($sp)',asm);self.assertRegex(asm,r'lwc1\s+\$f6,\s*0x58\(\$sp\)');self.assertIn('lw         $t9, 0x60($sp)',asm)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        direct=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==jal];literals=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
        self.assertEqual((direct,literals),([0xC68A4],[]));self.assertEqual(struct.unpack_from('>I',self.table,107*4)[0],0x150993C8)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.PARENT,12);self.assertNotEqual(old[at:at+12],rom[source.PARENT_ROM:source.PARENT_ROM+12])
        self.assertIn('s32 func_15097A8C() {\n    return 0;\n}',self.values['conker/src/game/generated_C4DC0.c'].decode())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=40,guards=0,bindings=4,neighbors=18,compact_functions=19,actual_Make_commands=5,default_O2_g3=True,all_diagnostics_empty=True,canonical_ABI='void(struct127*)',spawn_ABI='u8*(u8*,s32,f32,s32)',animate_ABI='void(pointer,u16,f32,f32,f32,f32,s32)',retail_direct_sites=direct,current_parent_remains_placeholder=True)
    def test_02_signed_index_snapshot_order_aliases_and_provider_effects(self):
        cases=[Case(slot,0,mutate,alias,phase)for slot,mutate,alias,phase in itertools.product(range(26),range(4),range(3),(0,8))]
        cases.extend(Case(slot,offset,mutate,alias,phase)for slot,offset,mutate,alias,phase in itertools.product((-2,-1,0,1,25,26),(0,1,3,7,811),range(4),(0,3),(0,8)))
        visits=set()
        for c in cases:visits.update(self.compare(c).visits)
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4)))
        self.receipt['guest']=dict(cases=len(cases),all_46_words_visited=True,all_26_valid_slots=True,signed_truncation_and_nonmultiple_guest_inputs=True,alias_layouts=4,pointer_reload_observable=True,provider_return_ignored=True,provider_before_and_after_flag_mutation=True,full_private_state_equal=True,invalid_native_indices_not_claimed=True)
    def test_03_original_and_retained_animation_early_exits(self):
        count=0
        for slot,mutate,busy,phase in itertools.product((0,1,25),range(4),(0,1),(0,8)):
            c=Case(slot=slot,mutate=mutate,phase=phase);initial=fixture(c);initial[BUSY]=busy;initial[VALID]=0;initial[actor_address(c)+4]=255
            for provider in(self.animate,self.retained_animate):
                connected={source.ANIMATE+i*4:w for i,w in enumerate(provider)};self.compare(c,initial,connected=connected,quiet_animate=True);count+=1
        self.receipt['provider']=dict(cases=count,original_and_retained_95_words_literal=True,actual_u16_home_and_f32_moves=True,only_busy_and_invalid_actor_early_exit_routes=True,larger_provider_semantics_bounded=True,no_helper_credit=True)
    def test_04_complete_original_dispatcher_target_route(self):
        count=0;visits=set()
        for slot,state,command,found,mutate,phase in itertools.product((0,25),(9,0x3B,0,255),(108,0,143),(False,True),(0,3),(0,8)):
            c=Case(slot=slot,mutate=mutate,phase=phase);initial=fixture(c)
            for i,b in enumerate(self.table):initial[source.TABLE+i]=b
            for i in range(32):initial[PACKET+i]=(i*13+0x5A)&255
            put(initial,PACKET+8,state);expected=dict(initial);calls=[(source.GET_ACTOR,(17,))];result=0
            if found and command==108:
                result=1
                if state==9:calls.append((source.OTHER,(actor_address(c),)))
                elif state==0x3B:
                    calls.append((source.ENTRY,(actor_address(c),)));expected,tail=reference(expected,c);calls.extend(tail)
            pair=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=TransitionOracle(self.parent,initial,c,source.PARENT,connected,arguments=(17,command,PACKET),found=found).run();visits.update(m.visits)
                self.assertEqual(m.calls,calls);self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['caller']=dict(cases=count,full_2146_word_retail_body_loaded=True,actual_142_entry_jump_table=True,event_108_state_0x3B=True,target_argument_from_lookup=True,lookup_and_other_state_handler_bounded=True,current_C_dispatcher_is_still_placeholder=True,whole_dispatcher_coverage_claimed=False,visited_dispatcher_words=len(set(range(source.PARENT,source.PARENT+8584,4))&visits))
    def test_05_native32_actual_C_layout_ABI_and_controls(self):
        text=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=26*256*4*2,effective_controls=len(controls()),real_SDK_layout_assertions=True,typed_function_pointer_interfaces=True,trapping_UBSan=True,properly_typed_global_actor_array_and_typeless_nested_allocations=True,valid_array_domains_only=True)
    def test_06_fault_prefixes_effective_compiled_negatives_and_stack_alias(self):
        count=0
        for c in(Case(),Case(slot=25,mutate=3),Case(alias=3),Case(slot=-1,offset=811)):
            m=self.compare(c);initial=fixture(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=TransitionOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        cached=source.SELECTED.replace('    entry->unk31C->unk78 = 0x3B;\n    entry->unk31C->unk11A = 2;','    struct126 *nested = entry->unk31C;\n    nested->unk78 = 0x3B;\n    nested->unk11A = 2;')
        unsigned=source.SELECTED.replace('((s32)actor - (s32)D_800CC2D0)','((u32)actor - (u32)D_800CC2D0)')
        for name,body,c in(('cached',cached,Case(alias=3)),('unsigned',unsigned,Case(slot=-1))):
            self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag)
            data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            with self.assertRaisesRegex(AssertionError,'nested state before spawn'if name=='cached'else'unmapped (read|store)'):TransitionOracle(words,fixture(c),c).run()
        for phase in(0,8):
            c=Case(phase=phase,actor_at=STACK+phase-0x83);initial=fixture(c);pair=[TransitionOracle(w,initial,c).run()for w in(self.truth,self.words)];self.assertEqual(complete(pair[0]),complete(pair[1]))
        self.receipt['faults']=dict(fired_prefix_pairs=count,compiled_cached_pointer_negative=True,compiled_unsigned_index_negative=True,guest_only_stack_alias_cases=2,hardware_fault_or_timing_claimed=False)
    def test_07_real_padder_and_GNU_rebases_no_guards(self):
        raw,bindings=source.checked_payload(*source.payload(self.obj))
        for data,rels in((raw[:-4],bindings),(bytes([raw[0]^1])+raw[1:],bindings),(raw,bindings|{4:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(data,rels)
        p=self.fresh/'fresh-padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        anchors=dict(D_800CC2D0=POOL,func_15083568=source.SPAWN,func_1505E650=source.ANIMATE);asm,missing=emit_function(raw,dict(value=0,size=184),bindings,source.FUNCTION,anchors);self.assertFalse(missing)
        p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        count=0
        for i,(entry,pool,spawn,animate)in enumerate(((source.ENTRY,POOL,source.SPAWN,source.ANIMATE),(0x15263570,0x81207FFC,0x15383568,0x1535E650),(0x15463570,0x81208000,0x15783568,0x1575E650))):
            anchors=dict(D_800CC2D0=pool,func_15083568=spawn,func_1505E650=animate);images=[]
            for j,object_ in enumerate((self.out/'original-func_15063570.o',obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in anchors.items()],'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for slot,offset,mutate,alias,phase in itertools.product((-1,0,25),(0,3),range(4),(0,3),(0,8)):
                self.compare(Case(slot,offset,mutate,alias,phase),images=images,entry=entry,pool=pool,symbols=dict(spawn=spawn,animate=animate));count+=1
        self.receipt['rebases']=dict(layouts=3,GNU_links=6,guest_cases=count,HI16_LO16_signed_carry=True,all_four_bindings=True,guards=0,raw_negative_controls=3)
    def test_08_strict_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184]
        expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos+8 for pos,name,f,_ in source.symbol_rows(before)if name==source.FUNCTION and f[1:3]==(source.ENTRY,12))
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(148,147,1,0));self.receipt['strict']=dict(changed_bytes=148,code_bytes=147,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(values),word_patch_manifest_unchanged=True)

if __name__=='__main__':unittest.main()
