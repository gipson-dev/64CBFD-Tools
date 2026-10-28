"""Object-record ensure: byte carrier/local home, callback return, providers and exact image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_object_record_ensure_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
TABLE,ALTERNATE,ACTOR,SCRIPT=0x70000,0x80000,0x90000,0xA0000
WINDOW,WINDOW_ROM,WINDOW_SIZE=0x150AE0F8,0xDB5A8,156
REGISTRY,REGISTRY_ROM=0x80088420,0x22CEE0
MASK=0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    selector:int=7
    incoming:int=0x12345678
    first:int=2
    present:bool=False
    actor_byte:int=128
    created:int=1
    second:int=5
    mode:int=0
    layout:int=0
    phase:int=0

def fixture(c,global_=source.GLOBAL):
    sp=STACK+c.phase;index=3 if c.mode==4 else c.first;offset=48*(index&MASK)&MASK
    base=TABLE
    if c.layout==1:base=(global_-2-offset)&MASK
    elif c.layout==2:base=(global_+3-2-offset)&MASK
    elif c.layout==3:base=(sp-9-2-offset)&MASK
    elif c.layout==4:base=(sp-1-2-offset)&MASK
    actor=sp+4-0x13F if c.layout==5 else ACTOR
    m={sp+i:(i*17+0xA5)&255 for i in range(-512,128)}
    for p,n in((TABLE,384),(ALTERNATE,384),(actor,0x150)):
        m.update({p+i:(i*13+0x59)&255 for i in range(n)})
    for p in(base,ALTERNATE):m[(p+offset+2)&MASK]=0xA5
    m[actor+0x13F]=c.actor_byte;put(m,global_,base);return m,actor

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+128}
def effect(m,c,stage,sp,global_):
    frame=sp-48
    for i in range(4):put(m,frame+4*i,0xB5000000+i)
    if c.mode==1 and stage=='first':put(m,sp,0x87654321);put(m,sp+4,0xABCDEF01)
    if c.mode==2 and stage=='actor':put(m,global_,ALTERNATE)
    if c.mode==3 and stage=='create':put(m,sp-12,0x7F)
    if c.mode==4 and stage=='actor':put(m,sp-4,3)

def reference(initial,c,actor,global_=source.GLOBAL,entered=None):
    m=dict(initial);sp=STACK+c.phase if entered is None else entered;frame=sp-48;put(m,sp+4,c.incoming);put(m,sp,c.selector);put(m,sp-12,c.selector&255);calls=[];observations=[]
    identity=c.selector&255;calls.append((source.FIND,(identity,)));effect(m,c,'first',sp,global_);index=c.first&MASK
    if index!=MASK:
        put(m,sp-4,index);identity=m[sp-9];calls.append((source.ACTOR,(identity,)));effect(m,c,'actor',sp,global_);index=read(m,sp-4)
        if c.present:index=m[actor+0x13F]
        else:
            offset=(48*index)&MASK;at=(read(m,global_)+offset+2)&MASK;m[at]=0;record=(read(m,global_)+offset)&MASK;put(m,frame+16,0);args=(record,index,0,0,0);calls.append((source.CREATE,args));observations.append((at,m[at],args));effect(m,c,'create',sp,global_)
            if not(c.created&MASK):return m,calls,observations,MASK
            identity=m[sp-9];calls.append((source.FIND,(identity,)));effect(m,c,'second',sp,global_);index=c.second&MASK
    return m,calls,observations,(index|0x2000 if index else 0)&MASK

class EnsureOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),actor=ACTOR,entry=source.ENTRY,connected=None,helpers=None,global_=source.GLOBAL,providers=(),real=False):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.selector,c.incoming),connected=connected)
        self.c,self.actor,self.global_,self.real=c,actor,global_,real;self.helpers=helpers or(source.FIND,source.ACTOR,source.CREATE);self.providers=set(providers)-{0};self.find_calls=0;self.observed=[];self.hi,self.lo=0x89ABCDEF,0x76543210;self.condition=True
    def record_call(self,target):
        if target==self.helpers[0]:count=1;self.find_calls+=1
        elif target==self.helpers[1]:count=1
        elif target==self.helpers[2]:count=5
        elif target in self.providers or target==source.ENTRY:count=2
        else:raise AssertionError(('unmapped callback',target))
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.helpers[2]:
            at=next(e[1]for e in reversed(self.events)if e[0]=='W'and e[2]==1);self.observed.append((at,self.memory[at],args))
    def hook(self,target):
        if target==self.helpers[0]:stage='first'if self.find_calls==1 else'second';value=self.c.first if self.find_calls==1 else self.c.second
        elif target==self.helpers[1]:stage='actor';value=self.actor if self.c.present else 0
        elif target==self.helpers[2]:stage='create';value=self.c.created
        else:stage='other';value=0x87654321
        effect(self.memory,self.c,stage,self.r[29]+48,self.global_)
        if self.real and target==self.helpers[2]and self.c.created:
            put(self.memory,source.GLOBAL,ALTERNATE)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.r[2]=value&MASK;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678

def controls():
    b=source.SELECTED
    result=dict(wrong_identity=b.replace('identity = selector;','identity = selector >> 8;'),wrong_missing=b.replace('index != -1','index > 0'),wrong_actor=b.replace('actor == NULL','actor != NULL'),wrong_state=b.replace('.state = 0;','.state = 1;'),wrong_fifth=b.replace('index, 0, 0, 0)','index, 0, 0, 1)'),wrong_actor_byte=b.replace('actor[0x13F]','actor[0x13E]'),wrong_tag=b.replace('0x2000','0x1000'))
    a=b.rfind('index = func_15083E0C(identity);');assert a>=0;result['missing_requery']=b[:a]+b[a:].replace('index = func_15083E0C(identity);','index = 6;',1)
    assert all(x!=b for x in result.values());return result

def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
static SpawnLookupRecord records[8],alternate[8],expected[8],expectedAlt[8];
SpawnLookupRecord *D_800D20FC;
static u8 actor[0x150];static u32 lookupCalls,actorCalls,createCalls,error,selectorWord,firstResult,secondResult,createdResult,present,redirect;
typedef s32(*Handler)(s32,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(SpawnLookupRecord)==48&&__builtin_offsetof(SpawnLookupRecord,state)==2)?1:-1];
__attribute__((noinline,noclone)) s32 func_15083E0C(u8 identity){
 if(identity!=(u8)selectorWord||lookupCalls>1)error=1;return(s32)(lookupCalls++?secondResult:firstResult);
}
__attribute__((noinline,noclone)) u8 *func_15083E90(u8 identity){
 if(identity!=(u8)selectorWord||lookupCalls!=1||actorCalls++)error=1;
 if(redirect)D_800D20FC=alternate;return present?actor:0;
}
__attribute__((noinline,noclone)) s32 func_15082A44(SpawnLookupRecord*p,s32 index,s32 a,s32 b,s32 fifth){
 if(createCalls++||lookupCalls!=1||actorCalls!=1||index!=(s32)firstResult||a||b||fifth||p!=D_800D20FC+index||p->state)error=1;
 return(s32)createdResult;
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''static int one(Handler fn,u32 word,u32 incoming,u32 scenario,u32 mode,u32 byte,u32 after,u32 indirect){
 u32 i,result,want;selectorWord=word;firstResult=scenario==0?0xFFFFFFFFu:scenario==1?0:scenario==2?7:2;
 present=scenario==1||scenario==2;createdResult=scenario==3?0:0x80000001u;secondResult=after;redirect=mode;
 for(i=0;i<sizeof(records);i++)((u8*)records)[i]=((u8*)expected)[i]=(i*13+0x59)&255;
 for(i=0;i<sizeof(alternate);i++)((u8*)alternate)[i]=((u8*)expectedAlt)[i]=(i*17+0xA5)&255;
 for(i=0;i<sizeof(actor);i++)actor[i]=(i*19+3)&255;actor[0x13F]=byte;
 D_800D20FC=records;lookupCalls=actorCalls=createCalls=error=0;
 if(scenario==0)want=0xFFFFFFFFu;
 else if(present)want=byte?byte|0x2000:0;
 else {if(mode)expectedAlt[firstResult].state=0;else expected[firstResult].state=0;want=scenario==3?0xFFFFFFFFu:after?after|0x2000u:0;}
 if(indirect){Handler volatile call=fn;result=(u32)call((s32)word,(u8)incoming);}else result=(u32)fn((s32)word,(u8)incoming);
 if(error||result!=want||lookupCalls!=(scenario==0||present||scenario==3?1:2)||actorCalls!=(scenario!=0)||createCalls!=(scenario!=0&&!present))return 1;
 for(i=0;i<sizeof(records);i++)if(((u8*)records)[i]!=((u8*)expected)[i])return 1;
 for(i=0;i<sizeof(alternate);i++)if(((u8*)alternate)[i]!=((u8*)expectedAlt)[i])return 1;
 return D_800D20FC!=(mode&&scenario!=0?alternate:records);
}
static int variant(Handler fn,u32 all){u32 c,h,s,m,d,b;for(c=0;c<256;c++)for(h=0;h<3;h++)for(s=0;s<5;s++)for(m=0;m<2;m++)for(d=0;d<2;d++)
 if(one(fn,c|(u32[]){0,0x12340000u,0xFFFFFF00u}[h],c^255,s,m,(u32[]){0,1,127,128,255}[c%5],(u32[]){0,1,0xFFFFFFFFu,0x80000000u,0x7FFFFFFFu,0x2000u}[c%6],d))return 23;
 if(all)for(b=0;b<256;b++){if(one(fn,0xFF000007u,b,2,0,b,0,1))return 23;if(one(fn,7,b,4,1,0,b,1))return 23;}
 return 0;}
int run(void){if(variant(selected,1))return 1;
'''
    for i,name in enumerate(controls()):text+='if(variant(%s,0)!=23)return %d;\n'%(name,11+i)
    return text+'return 0;}\n'+START,256*3*5*2*2+512

class ObjectRecordEnsureTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']));cls.window=list(struct.unpack_from('>39I',rom,WINDOW_ROM));cls.registry=struct.unpack_from('>15I',rom,REGISTRY_ROM)
        old=cls.values['conker/build/conker.us.elf'];cls.helpers={};cls.retained={}
        for entry,at,n in((source.FIND,0xB12BC,33),(source.ACTOR,0xB1340,72)):
            cls.helpers[entry]=list(struct.unpack_from('>%dI'%n,rom,at));cls.retained[entry]=list(struct.unpack_from('>%dI'%n,old,source.elf_slot_offset(old,entry,n*4)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,helpers=None,global_=source.GLOBAL):
        initial,actor=fixture(c,global_);expected,calls,observations,result=reference(initial,c,actor,global_);pair=[];hs=helpers or(source.FIND,source.ACTOR,source.CREATE);mapping=dict(zip(hs,(source.FIND,source.ACTOR,source.CREATE)))
        for words in images or(self.truth,self.words):
            m=EnsureOracle(words,initial,c,actor,entry,helpers=hs,global_=global_).run();self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.r[2],result,c);self.assertEqual([(mapping.get(t,t),a)for t,a in m.calls],calls,c);self.assertEqual(m.observed,observations,c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_actual_Make_ABI_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.helpers,self.retained);self.assertEqual(self.registry[1],source.ENTRY);self.assertEqual(self.words[0],0x27BDFFD0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),4)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_C4DC0.c.o.compact'),4);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];words=struct.unpack('>%dI'%(len(rom)//4),rom);self.assertEqual([4*i for i,w in enumerate(words)if w==source.ENTRY],[0x22CEE4]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in words))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=48,guards=0,bindings=6,neighbors=3,compact_functions=4,Make_commands=3,diagnostics_empty=True,ABI='s32(s32,u8)',incoming_second_word_overwritten=True,identity_home=36,index_home=44,registry_slot=1,registry_entries=15)
    def test_02_byte_carrier_return_boundaries_aliases_and_private_homes(self):
        count=0;visits=set()
        for selector,high,scenario,phase in itertools.product(range(256),(0,0x12340000,0xFFFFFF00),range(5),(0,8)):
            c=Case(selector|high,selector^0xFFFFFF00,first=-1 if scenario==0 else 2,present=scenario in(1,2),actor_byte=selector,created=0 if scenario==3 else 1,second=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x2000)[selector%6],phase=phase);visits.update(self.compare(c).visits);count+=1
        for mode,layout,phase,present in itertools.product(range(5),range(6),(0,8),(0,1)):self.compare(Case(mode=mode,layout=layout,phase=phase,present=bool(present)));count+=1
        for first,second,created in itertools.product((0,1,7,0x7FFFFFFF,0x80000000,0xFFFFFFFE),(0,0xFFFFFFFF,0x80000000),(0,1,0x80000000)):
            self.compare(Case(first=first,second=second,created=created));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)))
        self.receipt['guest']=dict(cases=count,all_47_words_visited=True,all_selector_and_actor_index_bytes=True,three_full_input_word_patterns=True,first_sentinel_and_post_query_fullword_returns=True,six_alias_layouts=True,five_provider_modes=True,local_identity_and_index_homes_qualified=True,complete_private_state_equal=True,sparse_or_wrapped_indices_guest_only=True)
    def test_03_authentic_interpreter_dispatch_window_and_return_consumer(self):
        count=0;visits=set();providers=set(self.registry)-{0}
        for kind,selector,high,scenario,phase in itertools.product((0,2,7,8,11,14,15),(0,1,127,128,255),(0,0x87600000),range(5),(0,8)):
            c=Case(selector|high,first=-1 if scenario==0 else 2,present=scenario in(1,2),actor_byte=selector,created=0 if scenario==3 else 1,phase=phase);initial,actor=fixture(c);word=(selector|high)&0xFFFF0FFF|kind<<12;put(initial,SCRIPT,word)
            for i,v in enumerate(self.registry):put(initial,REGISTRY+4*i,v)
            target=self.registry[kind-1]if kind else 0;masked=word&0xFFFF0FFF;calls=[];expected=dict(initial);result=0
            if kind:
                calls=[(target,(masked,SCRIPT))]
                if target==source.ENTRY:
                    child=Case(masked,SCRIPT,c.first,c.present,c.actor_byte,c.created,c.second,phase=phase);expected,extra,_,result=reference(expected,child,actor,entered=STACK+phase-16);calls+=extra
                else:result=0x87654321
            pair=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(words)};m=EnsureOracle(self.window,initial,c,actor,entry=WINDOW,connected=connected,providers=providers);m.r[4]=SCRIPT;m.before[23]=0xDEAD0000;m.run();self.assertEqual(m.calls,calls,(kind,selector,scenario));self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result);self.assertEqual(m.r[23],0xDEAD0000);pair.append(m);visits.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        c=Case();initial,actor=fixture(c);put(initial,SCRIPT,0x1007)
        for i,v in enumerate(self.registry):put(initial,REGISTRY+4*i,v)
        m=EnsureOracle(self.window,initial,c,actor,entry=WINDOW,providers=providers);m.r[4]=SCRIPT;m.before[23]=0xDEAD0000
        with self.assertRaisesRegex(AssertionError,'unmapped callback'):m.run()
        self.receipt['caller']=dict(cases=count,original_39_word_window=True,reachable_window_words=len(set(range(WINDOW,WINDOW+156,4))&visits),actual_15_entry_registry=True,selector_nibble_cleared_and_two_argument_envelope=True,S7_is_explicit_handwritten_return_carrier=True,zero_kind_returns_zero=True,null_entry_attempt_rejected=True,containing_interpreter_C_remains_placeholder=True,no_full_caller_acceptance_claimed=True)
    def test_04_native32_typed_calls_global_reload_and_controls(self):
        text,count=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=count,typed_s32_s32_u8_return_and_arguments=True,all_incoming_identity_and_actor_index_bytes=True,effective_controls=8,trapping_UBSan=True,valid_record_indices_only=True,helpers_are_bounded_contracts=True)
    def test_05_fault_prefixes_sparse_failures_and_real_lookup_helpers(self):
        count=0
        for c in(Case(first=-1),Case(present=True),Case(created=0),Case(),Case(layout=1),Case(mode=3),Case(mode=4)):
            initial,actor=fixture(c);m=self.compare(c)
            for cut in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=EnsureOracle(words,initial,c,actor);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));count+=1
        c=Case(first=-1);initial,actor=fixture(c);sparse={a:b for a,b in initial.items()if STACK-512<=a<STACK+128}
        for words in(self.truth,self.words):self.assertEqual(EnsureOracle(words,sparse,c,actor).run().r[2],MASK)
        integrations=0;helper_visits=set()
        for helpers in(self.helpers,self.retained):
            for identity,position,actor_slot,created,phase in itertools.product((0,1,128,255),(-1,0,3),(-1,0,25),(0,1),(0,8)):
                c=Case(identity,created=created,phase=phase);initial,_=fixture(c);count_records=4;put(initial,source.GLOBAL,TABLE);initial[0x800D2100]=count_records
                for p in(TABLE,ALTERNATE):
                    for i in range(count_records):initial[p+48*i+40]=(identity+1)&255
                if position>=0:initial[TABLE+48*position+40]=identity
                initial[ALTERNATE+48*2+40]=identity
                for i in range(26):put(initial,0x800CC2D0+0x32C*i,0);initial[0x800CC2D0+0x32C*i+0x3B]=(identity+1)&255
                actor=0
                if actor_slot>=0:actor=0x800CC2D0+actor_slot*0x32C;put(initial,actor,1);initial[actor+0x3B]=identity;initial[actor+0x13F]=actor_slot
                first=position if identity and position>=0 else -1;result=MASK if first<0 or actor_slot<0 and not created else (actor_slot|0x2000 if actor_slot else 0)if actor_slot>=0 else 0x2002;pair=[]
                connected={entry+4*i:w for entry,body in helpers.items()for i,w in enumerate(body)}
                for words in(self.truth,self.words):
                    m=EnsureOracle(words,initial,c,actor,connected=connected,real=True).run();self.assertEqual(m.r[2],result,(identity,position,actor_slot,created));pair.append(m);helper_visits.update(m.visits)
                self.assertEqual(complete(pair[0]),complete(pair[1]));integrations+=1
        self.receipt['faults_helpers']=dict(fired_prefix_pairs=count,sparse_missing_descriptor_needs_no_global_table_or_actor_mapping=True,original_retained_33_word_record_query_and_72_word_actor_query=True,helper_integrations=integrations,actor_array_last_slot_and_zero_identity=True,constructor_remains_bounded_contract=True,guest_only_fault_semantics=True,lookup_helper_words_visited=len(set(range(source.FIND,source.FIND+132,4))&helper_visits),actor_helper_words_visited=len(set(range(source.ACTOR,source.ACTOR+288,4))&helper_visits))
    def test_06_actual_padder_raw_controls_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
        for b,bindings in((raw[:-4],rs),(bytes([raw[0]^1])+raw[1:],rs),(raw,rs|{24:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        links=0;cases=0
        for i,(delta,global_)in enumerate(((0,source.GLOBAL),(0x200000,0x800E30FC),(0x10000000,0x8010F0FC))):
            entry=source.ENTRY+delta;hs=tuple(x+delta for x in(source.FIND,source.ACTOR,source.CREATE));symbols={'D_800D20FC':global_}|{'func_%08X'%a:b for a,b in zip((source.FIND,source.ACTOR,source.CREATE),hs)};asm,missing=emit_function(raw,dict(value=0,size=188),rs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(first=-1),Case(present=True),Case(created=0),Case(),Case(layout=1),Case(mode=4)):self.compare(c,images,entry,hs,global_);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,different_JAL_region_and_signed_low_carry=True,six_bindings_preserved=True,raw_negative_controls=3,guards=0)
    def test_07_compiled_access_order_negative_controls(self):
        cached=source.SELECTED.replace('    s32 index;','    SpawnLookupRecord *records = D_800D20FC;\n    s32 index;').replace('D_800D20FC[index]','records[index]');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+cached,'negative-cached-table');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mode=2);initial,actor=fixture(c);expected,_,_,_=reference(initial,c,actor);m=EnsureOracle(words,initial,c,actor).run();self.assertNotEqual(public(m.memory),public(expected))
        self.receipt['negative_order']=dict(actual_compiled_cached_table_mutant_rejected=True,global_provider_mutation_makes_stale_read_observable=True)
    def test_08_strict_full_image_inputs_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(141,140,1,0));self.receipt['strict']=dict(changed_bytes=141,code_bytes=140,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(v))
if __name__=='__main__':unittest.main()
