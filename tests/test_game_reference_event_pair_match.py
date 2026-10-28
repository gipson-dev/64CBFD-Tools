"""Paired reference events: real registry/dispatcher, live aliases, byte ABI and exact image."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_reference_event_pair_match as source
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
OWNER,STATE,EVENT,ALTERNATE=0x30000,0x70000,0x80000,0x90000
@dataclass(frozen=True)
class Case:
    command:int=0
    shape:int=0
    phase:int=0
    layout:int=0
    seed:int=0x5A
    mode:int=0

def fixture(c):
    sp=STACK+c.phase;state=sp+8 if c.layout==6 else OWNER+0x90 if c.layout==4 else OWNER+0x20 if c.layout==9 else STATE
    event=(EVENT,state,state-4,state+4,EVENT,OWNER+0x98,EVENT,sp,sp+8,EVENT)[c.layout]
    m={sp+i:(i*17+0xA5)&255 for i in range(-256,128)}
    for p,n in((OWNER,0x200),(state,32),(event,32),(ALTERNATE,32)):
        m.update({p+i:(i*13+c.seed)&255 for i in range(n)})
    a,b=0x11223344,0x55667788
    bound=(a,0x99AABBCC,b,0x99AABBCC,a)[c.shape]
    if c.shape==4:b=a
    put(m,event,a);put(m,event+4,b);m[event+8]=c.seed;m[event+9]=c.seed^255
    put(m,state,bound);m[state+4]=(m[event+4]if c.shape==1 else m[event+4]^255)
    put(m,OWNER+0x98,state);return m,event,state

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+128}
def effect(m,p,sp,mode=0,real=False):
    if real:
        ref=read(m,p+0x98);put(m,p+0x1E,read(m,p+0x1E,2)&0xFFFD,2);m[p+0x30]=0;m[ref+6]|=5
    else:
        m[p+0x31]^=0xA5
        if mode:put(m,p+0x98,ALTERNATE)
        for i in range(4):put(m,sp-24+4*i,0xB5000000+i)

def reference(initial,c,name,event,real=False,entered=None):
    m=dict(initial);sp=STACK+c.phase if entered is None else entered;put(m,sp+8,c.command);t=source.TARGETS[name];ref=read(m,OWNER+0x98);command=c.command&255;calls=[]
    if command in(0,2,t['special']):
        if read(m,ref)==read(m,event)or m[ref+4]==m[event+4]:
            calls=[(t['helper'],(OWNER,))];effect(m,OWNER,sp,c.mode,real)
    elif command==45:
        obj=read(m,event);current=read(m,ref)
        if obj==current:put(m,ref,read(m,event+4));m[ref+4]=m[event+9]
        elif read(m,event+4)==current:put(m,ref,obj);m[ref+4]=m[event+8]
    return m,calls

class ReferenceOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),name='func_15198054',event=EVENT,entry=None,connected=None,helper=None,providers=()):
        t=source.TARGETS[name];entry=t['entry']if entry is None else entry
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(OWNER,event,c.command),connected=connected)
        self.c,self.name,self.event=c,name,event;self.helper=t['helper']if helper is None else helper;self.providers=set(providers);self.hi,self.lo=0x89ABCDEF,0x76543210;self.condition=True
    def record_call(self,target):
        assert target==self.helper or target in self.providers or target in{t['entry']for t in source.TARGETS.values()},hex(target)
        args=self.arguments(1 if target==self.helper else 3);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.helper or target in self.providers
        if target==self.helper:
            self.memory[OWNER+0x31]^=0xA5
            if self.c.mode:put(self.memory,OWNER+0x98,ALTERNATE)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678

def controls(body):
    result=dict(missing_zero=body.replace('command == 0','command == 1',1),
      wrong_match=body.replace('||\n            (reference->identifier','&&\n            (reference->identifier'),
      wrong_identifier=body.replace('identifier == event[4]','identifier == event[5]'),
      wrong_first_object=body.replace('reference->object = *(u8 **)(event + 4);','reference->object = object;'),
      wrong_first_id=body.replace('identifier = event[9]','identifier = event[8]'),
      wrong_second_object_test=body.replace('reference->object == *(u8 **)(event + 4)','reference->object == *(u8 **)event'),
      wrong_second_id=body.replace('identifier = event[8]','identifier = event[9]'),
      wrong_replace_command=body.replace('command == 0x2D','command == 0x2E'))
    assert all(x!=body for x in result.values());return result

def native_harness(values,registry):
    text=source.HEADERS+source.DECLARATIONS+'''
typedef void(*Handler)(u8*,s32,u8);
typedef struct {u8 prefix[0x1E];u16 flags;s32 selector;u8 reserved24[0x74];BoundObjectReference *reference;u8 tail[0x64];} Owner;
typedef struct {u8 *first,*second;u8 ids[2],pad[2];} Event;
static Owner owner,expectedOwner;static BoundObjectReference state,expectedState;static Event event;
static u8 objects[3][16];static u32 calls,error,otherCalls,which,expectedCalls,expectedCommand;
Handler D_8008A390[20];
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(BoundObjectReference)==8&&
 __builtin_offsetof(BoundObjectReference,identifier)==4&&__builtin_offsetof(Owner,reference)==0x98&&
 __builtin_offsetof(Owner,selector)==0x20&&__builtin_offsetof(Event,second)==4&&__builtin_offsetof(Event,ids)==8)?1:-1];
'''
    lo,hi=source.function_span(values[source.SOURCE].decode(),'func_151993B4');text+=values[source.SOURCE].decode()[lo:hi].replace('func_151993B4','real_first')+'\n'
    text+='''static void check(u8*p,u32 id){if(p!=(u8*)&owner||id!=which||!expectedCalls||calls++)error=1;}
__attribute__((noinline,noclone)) void func_151993B4(u8*p){check(p,0);real_first(p);}
__attribute__((noinline,noclone)) void func_1516972C(u8*p){check(p,1);p[0x31]^=0xA5;}
static void other(u8*p,s32 address,u8 command){if(p!=(u8*)&owner||(u32)address!=(u32)&event||command!=expectedCommand||otherCalls++)error=1;}
'''
    variants=[]
    for i,(name,body)in enumerate(source.SELECTED.items()):
        for label,b in dict(selected=body,**controls(body)).items():
            ident='f%d_%s'%(i,label);text+=b.replace(name,ident)+'\n';variants.append((i,label,ident))
    parent=values['conker/src/game/generated_174BF0.c'].decode();lo,hi=source.function_span(parent,'func_15147D1C');text+=parent[lo:hi]+'\n'
    text+='static const u32 registry[20]={'+','.join('0x%Xu'%v for v in registry)+'};\n'
    text+='''static int one(Handler fn,u32 id,u32 command,u32 shape,u32 seed,u32 indirect,u32 selector){
 u32 j,c=command&255;u8 *p=(u8*)&owner,*q=(u8*)&expectedOwner;u32 slot=id?14:3,special=id?38:8,active=!indirect||selector==slot;
 for(j=0;j<sizeof(owner);j++)p[j]=(j*13+seed)&255;
 for(j=0;j<sizeof(state);j++)((u8*)&state)[j]=(j*11+seed)&255;
 for(j=0;j<sizeof(event);j++)((u8*)&event)[j]=(j*7+seed)&255;
 owner.selector=selector;owner.reference=&state;event.first=objects[0];event.second=shape==4?objects[0]:objects[1];event.ids[0]=seed;event.ids[1]=seed^255;
 state.object=shape==0||shape==4?event.first:shape==2?event.second:objects[2];state.identifier=shape==1?((u8*)&event)[4]:((u8*)&event)[4]^255;
 expectedOwner=owner;expectedState=state;calls=otherCalls=error=0;which=id;expectedCommand=c;
 expectedCalls=active&&(c==0||c==2||c==special)&&(state.object==event.first||state.identifier==((u8*)&event)[4]);
 if(expectedCalls){if(!id){expectedOwner.flags&=0xFFFD;((u8*)&expectedOwner)[0x30]=0;((u8*)&expectedState)[6]|=5;}else((u8*)&expectedOwner)[0x31]^=0xA5;}
 if(active&&c==45){if(expectedState.object==event.first){expectedState.object=event.second;expectedState.identifier=event.ids[1];}
 else if(expectedState.object==event.second){expectedState.object=event.first;expectedState.identifier=event.ids[0];}}
 if(indirect){for(j=0;j<20;j++)D_8008A390[j]=registry[j]?other:0;D_8008A390[slot]=fn;func_15147D1C((u8*)&owner,(s32)&event,(u8)command);}
 else {Handler volatile call=fn;call((u8*)&owner,(s32)&event,(u8)command);}
 if(error||calls!=expectedCalls||otherCalls!=(indirect&&selector!=slot&&registry[selector]!=0))return 1;
 for(j=0;j<sizeof(owner);j++)if(p[j]!=q[j])return 1;
 for(j=0;j<sizeof(state);j++)if(((u8*)&state)[j]!=((u8*)&expectedState)[j])return 1;
 return 0;
}
static int variant(Handler fn,u32 id,u32 selected){u32 c,s,b,d,k;for(c=0;c<256;c++)for(s=0;s<5;s++)for(b=0;b<4;b++)for(d=0;d<2;d++)
 if(one(fn,id,c,s,(u32[]){0,127,128,255}[b],d,id?14:3))return 23;
 if(selected)for(k=0;k<20;k++)for(c=0;c<5;c++)if(one(fn,id,(u32[]){0,2,8,38,45}[c],c%5,0x59,1,k))return 23;
 return 0;}
int run(void){
'''
    for i,label,ident in variants:text+='if(variant(%s,%d,%d)!=%d)return %d;\n'%(ident,i,label=='selected',0 if label=='selected'else 23,1+len(text)%200)
    return text+'return 0;}\n'+START,256*5*4*2+20*5

class ReferenceEventPairTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'qualified-padded.o',source.OWNER);cls.truth={};cls.words={};cls.raw={}
        for n,t in source.TARGETS.items():cls.truth[n]=list(struct.unpack_from('>47I',rom,t['rom']));cls.words[n]=list(struct.unpack_from('>47I',data,fs[n]['value']));d,f=source.link_owner(ROOT,cls.fresh,cls.out/'after-owner.o',source.OWNER);cls.raw[n]=list(struct.unpack_from('>47I',d,f[n]['value']))
        cls.parent=list(struct.unpack_from('>18I',rom,source.PARENT_ROM));cls.helper=list(struct.unpack_from('>12I',rom,0x1C6864));cls.registry=struct.unpack_from('>20I',rom,source.TABLE_ROM);old=cls.values['conker/build/conker.us.elf'];cls.retained_parent=list(struct.unpack_from('>18I',old,source.elf_slot_offset(old,source.PARENT,72)));cls.retained_helper=list(struct.unpack_from('>12I',old,source.elf_slot_offset(old,0x151993B4,48)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c,name,images=None,entry=None,helper=None,real=False,helper_words=None):
        initial,event,state=fixture(c);expected,calls=reference(initial,c,name,event,real);pair=[];t=source.TARGETS[name]
        for words in images or(self.truth[name],self.raw[name],self.words[name]):
            connected={0x151993B4+4*i:w for i,w in enumerate(helper_words or self.helper)}if real else None
            m=ReferenceOracle(words,initial,c,name,event,entry,connected,helper).run();self.assertEqual(public(m.memory),public(expected),(name,c));self.assertEqual([(t['helper']if target==helper else target,a)for target,a in m.calls],calls);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m))
        return pair[0]
    def test_01_complete_owner_actual_Make_registry_and_callback_ABI(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.parent,self.retained_parent);self.assertEqual(self.helper,self.retained_helper)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),69)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',source.FUNCTIONS),67);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1C2C60.c.o.compact'),69);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];allwords=struct.unpack('>%dI'%(len(rom)//4),rom)
        for name,t in source.TARGETS.items():
            self.assertEqual(self.registry[t['slot']],t['entry']);self.assertEqual([4*i for i,w in enumerate(allwords)if w==t['entry']],[source.TABLE_ROM+4*t['slot']]);self.assertFalse(any(w in(0x0C000000|(t['entry']>>2&0x3FFFFFF),0x08000000|(t['entry']>>2&0x3FFFFFF))for w in allwords));self.assertEqual(self.words[name][0],0x27BDFFE8)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(functions=2,words_each=47,frame_each=24,guards_each=1,call_bindings_each=1,neighbors=67,compact_functions=69,Make_commands=3,diagnostics_empty=True,registry_slots=[3,14],registry_entries=20,ABI='void(u8*,s32,u8)',void_return_not_promoted_from_incidental_V0=True)
    def test_02_all_commands_unsigned_IDs_ordered_aliases_and_raw_C(self):
        count=0;coverage={}
        for name in source.FUNCTIONS:
            visits=set()
            for command,high,shape,phase in itertools.product(range(256),(0,0x12340000,0xFFFFFF00),range(5),(0,8)):
                m=self.compare(Case(command|high,shape,phase),name);visits.update(m.visits);count+=1
            for seed,command,shape in itertools.product(range(256),(0,45),(0,1,2)):self.compare(Case(command,shape,seed=seed),name);count+=1
            for layout,command,shape,phase in itertools.product(range(1,10),(0,2,source.TARGETS[name]['special'],45,255),range(5),(0,8)):self.compare(Case(command,shape,phase,layout),name);count+=1
            t=source.TARGETS[name];missing=set(range(t['entry'],t['entry']+188,4))-visits;self.assertEqual(missing,{t['entry']+100,t['entry']+148});coverage[name]=dict(reachable_words=45,literal_words=47,dead_duplicate_words=[25,37])
        self.receipt['guest']=dict(cases=count,all_256_commands_and_identifier_bytes=True,three_incoming_upper_word_patterns=True,ordered_alias_layouts=10,raw_original_and_normalized_complete_private_states_equal=True,coverage=coverage)
    def test_03_complete_original_retained_dispatcher_and_actual_registry(self):
        count=0;visits=set()
        for parent in(self.parent,self.retained_parent):
            for selector,command,shape,phase in itertools.product(range(20),(0,2,8,38,45,255),(0,1,2,3,4),(0,8)):
                c=Case(command,shape,phase);initial,event,state=fixture(c);put(initial,OWNER+0x20,selector)
                for i,v in enumerate(self.registry):put(initial,source.TABLE+4*i,v)
                target=self.registry[selector];name=next((n for n,t in source.TARGETS.items()if t['entry']==target),source.FUNCTIONS[0]);expected=dict(initial);calls=[]
                if target:
                    calls=[(target,(OWNER,event,command))]
                    if target in{t['entry']for t in source.TARGETS.values()}:expected,extra=reference(expected,c,name,event,entered=STACK+phase-24);calls+=extra
                pair=[]
                for images in(self.truth,self.raw,self.words):
                    connected={t['entry']+4*i:w for n,t in source.TARGETS.items()for i,w in enumerate(images[n])};m=ReferenceOracle(parent,initial,c,name,event,entry=source.PARENT,connected=connected,providers=self.registry).run();self.assertEqual(m.calls,calls,(selector,command,shape));self.assertEqual(public(m.memory),public(expected));pair.append(m);visits.update(m.visits)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m))
                count+=1
        self.assertTrue(set(range(source.PARENT,source.PARENT+72,4))<=visits)
        # The retail dispatcher uses a full-word index without clamping. These
        # sparse wrapped effective-index cases are guest-only, never C array UB.
        for selector in(0x40000003,0x80000003,0xC000000E,0xFFFFFFF3):
            c=Case(45,2);initial,event,state=fixture(c);put(initial,OWNER+0x20,selector);at=(source.TABLE+4*selector)&0xFFFFFFFF;target=source.TARGETS[source.FUNCTIONS[0]]['entry'];put(initial,at,target);pair=[]
            for images in(self.truth,self.words):
                connected={target+4*i:w for i,w in enumerate(images[source.FUNCTIONS[0]])};pair.append(ReferenceOracle(self.parent,initial,c,event=event,entry=source.PARENT,connected=connected,providers=self.registry).run())
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['callers']=dict(cases=count,complete_original_and_retained_18_word_dispatcher=True,all_20_actual_registry_entries=True,three_argument_callback_envelopes=True,no_return_consumer=True,fullword_index_sparse_wrap_cases=4,other_callbacks_are_bounded_contracts=True)
    def test_04_native32_actual_dispatcher_first_helper_and_controls(self):
        text,count=native_harness(self.values,self.registry)
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_target_each_profile=count,typed_three_argument_indirect_calls=True,actual_dispatcher_and_first_helper_C=True,second_helper_bounded_contract=True,effective_controls_each_target=8,trapping_UBSan=True,storage_overlap_qualified_in_guest_only=True)
    def test_05_fault_prefixes_sparse_paths_and_original_first_helper(self):
        count=0;integrations=0
        for name in source.FUNCTIONS:
            for command,shape in((0,0),(0,3),(45,0),(45,2),(45,3),(255,0)):
                c=Case(command,shape);initial,event,state=fixture(c);m=self.compare(c,name)
                for cut in range(m.root_accesses):
                    pair=[]
                    for words in(self.truth[name],self.raw[name],self.words[name]):
                        x=ReferenceOracle(words,initial,c,name,event);x.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):x.run()
                        self.assertEqual(x.root_accesses,cut);pair.append(x)
                    for x in pair[1:]:self.assertEqual(complete(pair[0]),complete(x));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(x.current_pc,x.delay_of))
                    count+=1
            c=Case(255);initial,event,state=fixture(c);sparse={a:b for a,b in initial.items()if STACK-256<=a<STACK+128 or OWNER+0x98<=a<OWNER+0x9C}
            for words in(self.truth[name],self.words[name]):self.assertFalse(ReferenceOracle(words,sparse,c,name,event).run().calls)
            # A matching object bypasses the optional ID-byte read.
            c=Case(0);initial,event,state=fixture(c)
            for p in(state+4,event+4):
                for i in range(4):initial.pop(p+i,None)
            for words in(self.truth[name],self.words[name]):self.assertEqual(len(ReferenceOracle(words,initial,c,name,event).run().calls),1)
        for helper in(self.helper,self.retained_helper):
            for command,shape,phase in itertools.product((0,2,8,45),(0,1,2,3,4),(0,8)):self.compare(Case(command,shape,phase),source.FUNCTIONS[0],real=True,helper_words=helper);integrations+=1
        self.receipt['faults']=dict(fired_prefix_triples=count,sparse_unknown_needs_only_owner_reference_pointer_and_stack=True,short_circuit_object_match_needs_no_ID_bytes=True,original_retained_first_helper_12_word_integrations=integrations,second_helper_remains_bounded=True,guest_only_fault_semantics=True)
    def test_06_symmetric_guard_closure_corruptions_and_actual_padder(self):
        payloads={n:source.checked_payload(n,*source.payload(self.out/'selected.o',n))for n in source.FUNCTIONS};old=self.values['conker/retail_word_patches.us.csv'];guards=source.guard_bytes(old,payloads);self.assertEqual(guards,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(guards.startswith(old));self.assertEqual(len(guards[len(old):].splitlines()),2)
        negatives=0
        for n,(raw,rs)in payloads.items():
            fitted,updated=source.normalized(n,raw,rs);self.assertEqual(updated,rs);self.assertEqual([i for i,(a,b)in enumerate(zip(struct.unpack('>47I',raw),struct.unpack('>47I',fitted)))if a!=b],[38])
            for word in range(47):
                bad=bytearray(raw);bad[4*word]^=1
                with self.assertRaises(ValueError):source.normalized(n,bytes(bad),rs)
                negatives+=1
            with self.assertRaises(ValueError):source.normalized(n,raw,{84:[('R_MIPS_26','wrong')]})
        reader=csv.DictReader(io.StringIO(guards.decode()));rows=list(reader)
        for name in source.FUNCTIONS:
            changed=[dict(row)for row in rows];row=next(x for x in changed if x['function']==name);row['expected']='0x544B0004';p=self.fresh/('bad-'+name+'.csv');s=io.StringIO();w=csv.DictWriter(s,fieldnames=reader.fieldnames);w.writeheader();w.writerows(changed);p.write_text(s.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        for a,b in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),repeat=2):self.assertEqual(a!=b,b!=a)
        self.receipt['guards']=dict(raw_word_negative_controls=negatives,wrong_bindings=2,actual_padder_corruptions=2,guards_each=1,only_symmetric_BNEL_sources_swapped=True,opcode_offset_delay_and_relocations_unchanged=True,old_manifest_bytes_preserved=True)
    def test_07_independent_GNU_rebases(self):
        count=0;links=0
        for name,t in source.TARGETS.items():
            fitted,rs=source.normalized(name,*source.payload(self.out/'selected.o',name));asm,missing=emit_function(fitted,dict(value=0,size=188),rs,name,{'func_%08X'%t['helper']:t['helper']});self.assertFalse(missing);p=self.fresh/('rebase-'+name+'.s');p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
            for i,delta in enumerate((0,0x200000,0x10000000)):
                images=[];entry=t['entry']+delta;helper=t['helper']+delta
                for j,object_ in enumerate((self.out/('original-'+name+'.o'),obj)):
                    p=self.fresh/('link-%s-%d-%d.ld'%(name,i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',name,'--defsym=func_%08X=0x%X'%(t['helper'],helper),'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
                self.assertEqual(*images)
                for command,shape in((0,0),(45,0),(45,2),(255,3)):self.compare(Case(command,shape),name,images,entry,helper);count+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts_each=3,guest_cases=count,different_JAL_region=True,call_bindings_fixed=True)
    def test_08_strict_whole_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];rom=values['conker/conker.us.bin'];expected=source.predicted_image(before,rom);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),rom);offsets=[20,source.elf_slot_offset(before,0x80082B20,4)]
        for n,t in source.TARGETS.items():offsets.extend((source.elf_slot_offset(before,t['entry'],188),source.elf_slot_offset(before,t['entry'],188)+188,next(p for p,name,f,_ in source.symbol_rows(before)if name==n)+8))
        for at in offsets:
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,rom)
        for bad in(before[:-1],bytes([before[0]^1])+before[1:]):
            with self.assertRaises(ValueError):source.check_image(bad,expected,rom)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(256,254,2,0));self.receipt['strict']=dict(changed_bytes=256,code_bytes=254,metadata_bytes=2,exclusions=0,corruptions=len(offsets)+2,wrong_predecessors=2,focused_inputs=len(values))
if __name__=='__main__':unittest.main()
