"""Indexed menu descriptor: guest order, original callers and factory connection."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_menu_record_descriptor_reset_oracle as prior
r=Path.cwd();o=r/'conker/build/game-menu-indexed-record-150B76BC-match';F='func_150B76BC';ENTRY=0x150B76BC;BODY=236
OLD,OUTPUT,OTHER=0x30000,0x40000,0x50000
CTOR,ALLOC,COPY=0x15169900,0x15167A68,0x10023A10
SYMS=dict(D_800D9898=0x800D9898,D_800D9890=0x800D9890,D_800918E8=0x800918E8,func_1516972C=0x1516972C,func_15169968=0x15169968)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 x:int=60
 slot:int=1
 old:int=OLD
 result:int=OUTPUT
 state:int=37
 mutation:int=0
 phase:int=0
 seed:int=0
 connected:int=0

def packet(c):return STACK+c.phase-60
def location(c,s=SYMS):return u32(s['D_800D9898']+u32(c.slot)*4)
def fields(c,s=SYMS):
 rows=prior.fields(dict(D_800918DC=s['D_800918E8']))
 return [(at,struct.unpack('>I',struct.pack('>f',signed(c.x)))[0] if at==0x1C else 0x432A0000 if at==0x20 else 64 if at==0x2E else v,n)for at,v,n in rows]
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
 for base,n in ((OLD,128),(OUTPUT,128),(OTHER,128),(s['D_800D9898']-8,64),(location(c,s)-4,12),(s['D_800D9890']-4,12)):
  for i in range(n):m[u32(base+i)]=(i*29+c.seed*11+0x59)&255
 put(m,location(c,s),c.old);m[s['D_800D9890']]=c.state
 return m
def release_effect(m,c,s=SYMS):
 if c.mutation&1:put(m,location(c,s),OTHER)
 if c.mutation&2:m[s['D_800D9890']]=0x5A
 if c.mutation&4:put(m,packet(c)+0x14,0xFEDC,2);m[packet(c)+7]^=0x55
def create_effect(m,c,s=SYMS):
 if c.mutation&8:put(m,packet(c)+0x14,99,2);m[packet(c)+7]^=0xA5
 if c.mutation&16:put(m,location(c,s),OTHER);m[s['D_800D9890']]=0xA7
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def reference(initial,c,s=SYMS):
 m=dict(initial);p=packet(c);at=location(c,s);calls=[];obs=[];fs=fields(c,s)
 for offset,value,n in fs:
  if offset in(0x30,0x2E):put(m,p+offset,value,n)
 old=read(m,at)
 for offset,value,n in fs:
  if offset not in(0x30,0x2E):put(m,p+offset,value,n)
 if old:calls.append((s['func_1516972C'],(old,)));release_effect(m,c,s)
 calls.append((s['func_15169968'],(p,)));obs.append((data(m,p,60),read(m,at),m[s['D_800D9890']]))
 if c.connected:calls.extend(((CTOR,(p,255)),(ALLOC,(94,0,76,0,255,1))))
 create_effect(m,c,s)
 if c.connected and c.result:
  calls.append((COPY,(p,c.result+16,60)));copied=data(m,p,60)
  for i,b in enumerate(copied):m[c.result+16+i]=b
 put(m,at,c.result)
 return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,arguments=None):
  self.descriptor_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(u32(c.x),u32(c.slot))if arguments is None else arguments);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={self.syms['func_1516972C']:1,self.syms['func_15169968']:1,CTOR:2,ALLOC:6,COPY:3,ENTRY:2};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_15169968']:self.descriptor_observations.append((data(self.memory,a[0],60),read(self.memory,location(self.case,self.syms)),self.memory[self.syms['D_800D9890']]))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  if t==s['func_1516972C']:release_effect(self.memory,c,s);value=0xDEADBEEF
  elif t in(s['func_15169968'],ALLOC):
   assert a==((packet(c),)if t==s['func_15169968']else(94,0,76,0,255,1)),a
   create_effect(self.memory,c,s);value=c.result
  else:
   assert t==COPY and a==(packet(c),c.result+16,60),(t,a);copied=data(self.memory,a[0],a[2])
   for i,b in enumerate(copied):self.memory[a[1]+i]=b
   value=0xAABBCCDD
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def linked(obj,label,s=SYMS,entry=ENTRY):
 from tools.experiments.alternative_source_draft_word_screen import emit_function
 from tools.pad_generated_object import parse_object
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown
 from tools.experiments.game_four_head_lookup_match import payload
 n=len(payload(obj,F)[0]);p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(n//4),sections(p.with_suffix('.elf'))['.text'][1][:n]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.descriptor_observations)
def verify(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.descriptor_observations)==(public(want),calls,obs),c
 assert data(m.memory,packet(c),60)==data(want,packet(c),60),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def cases():
 return [Case(x,slot,old,result,mutation=mu,seed=(slot+x)&255)for x,slot,old,result,mu in itertools.product((-2147483648,-16777217,-1,0,60,230,16777217,2147483647),(0,1,2,9,-1,0x3FFFFFFF),(0,OLD),(0,OUTPUT),(0,1,8,31))]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[2] and ps[0]!=ps[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:
   m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(),Case(old=0),Case(result=0,mutation=31),Case(x=-16777217,slot=-1,mutation=8,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800D9898=0x80007FF0+k*0x100000,D_800D9890=0x80018000+k*0x100000,D_800918E8=0x80028000+k*0x100000,func_1516972C=0x10008000+k*0x10000,func_15169968=0x10018000+k*0x10000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for x,slot,old,result,mu in itertools.product((-2147483648,2147483647),(1,9),(0,OLD),(0,OUTPUT),(0,31)):
   c=Case(x,slot,old,result,mutation=mu);initial=fixture(c,s);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 aliases=0
 for offset in(0,0x14,0x2C):
  c=Case(slot=0,mutation=8);s=dict(SYMS);s['D_800D9898']=packet(c)+offset;initial=fixture(c,s);programs=[linked(p,'alias-'+str(aliases)+'-'+str(i),s)for i,p in enumerate(objects)];machines=[]
  for words in programs:m=Oracle(words,initial,c,s);m.run();verify(m,initial,c,s);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helpers={}
 for entry,off,n in((CTOR,0x196DB0,26),(SYMS['func_15169968'],0x196E18,8)):helpers.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 connected_count=0
 for x,slot,old,result,mu in itertools.product((-16777217,60,230),(1,2),(0,OLD),(0,OUTPUT),(0,1,8,31)):
  c=Case(x,slot,old,result,mutation=mu,connected=1);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c,connected=helpers);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 caller_count=0;caller_visited=set()
 for pc,off,x,slot in((0x150B765C,0xE4B0C,60,1),(0x150B768C,0xE4B3C,230,2)):
  words=list(struct.unpack_from('>12I',rom,off));assert words[3]==0x0D42DDAF and words[4]==0x24050000+slot
  for old,result,mu in itertools.product((0,OLD),(0,OUTPUT),(0,1,8,31)):
   c=Case(x,slot,old,result,mutation=mu,phase=-24);initial=fixture(c);want,calls,obs=reference(initial,c);want[SYMS['D_800D9890']]=3
   for target in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),target));start=replace(c,phase=0);m=Oracle(words,initial,start,entry=pc,connected=code,arguments=());m.case=c;m.run();caller_visited.update(m.visits)
    assert(public(m.memory),m.calls,m.descriptor_observations)==(public(want),[(ENTRY,(x,slot))]+calls,obs),('caller',c)
    assert m.r[29]==STACK and m.r[16:24]==m.before[16:24]
   caller_count+=1
 assert all(pc in caller_visited for begin in(0x150B765C,0x150B768C)for pc in range(begin,begin+48,4))
 return dict(cases=count,executions=count*3,covered_words=len(visited),compiler_words=59,frame=96,guards=3,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_stack_global_alias_cases=aliases,original_factory_helper_words=34,connected_factory_cases=connected_count,complete_original_callers=2,caller_words=24,caller_cases=caller_count,caller_JAL_ROM=['0xE4B18','0xE4B48'],signed_full_word_x_to_float32=True,all_ten_table_slots_native_scope=True,full_guest_index_width=True,captured_old_pointer_and_live_helper_mutations=True,descriptor_bytes=60,defined_descriptor_bytes=40,unwritten_descriptor_bytes=20,raw_and_normalized_literal_full_state_equal=True,full_gameplay_or_hardware_claimed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_active_record_lookup_match import compile_owner
import sys
oracle=sys.modules[__name__]

def controls(body):
 indexed='((void **)D_800D9898)[slot]'
 return dict(inverted_release=body.replace('!= NULL','== NULL'),wrong_asset=body.replace('descriptor.asset = D_800918E8','descriptor.asset = D_800918E8 + 4'),narrowed_x=body.replace('(f32)x','(f32)(s16)x'),wrong_y=body.replace('170.0f','169.0f'),wrong_width=body.replace('field2E = 64','field2E = 63'),wrong_height=body.replace('field2C = 88','field2C = 87'),wrong_mode=body.replace('field30 = 6','field30 = 5'),wrong_parameter=body.replace('field37 = 21','field37 = 20'),wrong_scale=body.replace('field28 = 81','field28 = 80'),wrong_slot=body.replace(indexed,'((void **)D_800D9898)[0]'),discarded_result=body.replace(indexed+' = func_15169968(&descriptor);','func_15169968(&descriptor);'),cleared_before_create=body.replace(indexed+' = func_15169968(&descriptor);',indexed+' = NULL;\n    '+indexed+' = func_15169968(&descriptor);'),early_state=body.replace('    descriptor.field31 = 1;','    D_800D9890 = 3;\n    descriptor.field31 = 1;'))

def harness(selected):
 declaration=selected[selected.index('typedef struct'):selected.index('/* Replace')];body=selected[selected.index('/* Replace'):];bad=controls(body);assert len(bad)==13 and all(text!=body for text in bad.values())
 pre='#include <ultra64.h>\n'+declaration+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(MenuRecordDescriptorE4070)==60,"descriptor");
_Static_assert(__builtin_offsetof(MenuRecordDescriptorE4070,field1C)==0x1C,"x");
_Static_assert(__builtin_offsetof(MenuRecordDescriptorE4070,field39)==0x39,"last");
u8 D_800D9898[40] __attribute__((aligned(8))),D_800D9890,D_800918E8[12];
static u8 oldObject[128],newObject[128],otherObject[128];
typedef struct {s32 x,slot;u32 old,result,mutation,state,xbits;} Fixture;
static const Fixture *current;static u32 released,created,bad;
static void* pointer(u32 id){return id==0x30000?oldObject:id==0x40000?newObject:id==0x50000?otherObject:0;}
static u32 canonical(void*p){return p==oldObject?0x30000:p==newObject?0x40000:p==otherObject?0x50000:p?0xDEADBEEF:0;}
static void **selected(void){return ((void**)D_800D9898)+current->slot;}
void func_1516972C(void*p){if(!p||canonical(p)!=current->old||released||created)bad=1;released++;
 if(current->mutation&1)*selected()=otherObject;if(current->mutation&2)D_800D9890=0x5A;}
void *func_15169968(void *packet){MenuRecordDescriptorE4070*d=packet;u32 expectedOld=current->old,expectedState=current->state;union{f32 f;u32 u;} x;
 if(current->old){if(current->mutation&1)expectedOld=0x50000;if(current->mutation&2)expectedState=0x5A;}
 if(created||released!=(current->old?1u:0u)||canonical(*selected())!=expectedOld||D_800D9890!=expectedState)bad=2;
 x.f=d->field1C;
 if(d->asset!=D_800918E8||d->field14||d->field16||d->field18||x.u!=current->xbits||d->field20!=170.0f||d->field24||d->field26||d->field28!=81||d->field2A!=81||d->field2C!=88||d->field2E!=64||d->field30!=6||d->field31!=1||d->field32!=255||d->field33||d->field34||d->field35!=255||d->field36!=7||d->field37!=21||d->field38!=1||d->field39)bad=3;
 created++;if(current->mutation&8){d->field14=99;d->reserved04[3]=0xA5;}if(current->mutation&16){*selected()=otherObject;D_800D9890=0xA7;}
 return pointer(current->result);}
'''
 pre+='\n'.join(text.replace('func_150B76BC','test_'+name)for name,text in dict(selected=body,**bad).items())
 rows=[]
 for x,slot,old,result,mu,state in itertools.product((-2147483648,-16777217,-1,0,60,230,16777217,2147483647),range(10),(0,0x30000),(0,0x40000),(0,1,2,3,8,16,24,27),(0,37,255)):
  bits=struct.unpack('>I',struct.pack('>f',x))[0];rows.append('{'+','.join([str(x),str(slot),hex(old)+'u',hex(result)+'u',str(mu),str(state),hex(bits)+'u'])+'}')
 pre+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 pre+=r'''
typedef void(*Fn)(s32,s32);
static s32 check(Fn fn){u32 n,i;void*expected[10];for(n=0;n<CASE_COUNT;n++){current=fixtures+n;released=created=bad=0;
 for(i=0;i<10;i++){expected[i]=otherObject;((void**)D_800D9898)[i]=expected[i];}
 *selected()=pointer(current->old);D_800D9890=(u8)current->state;fn(current->x,current->slot);
 expected[current->slot]=pointer(current->result);
 if(bad||created!=1||released!=(current->old?1u:0u)||canonical(*selected())!=current->result||D_800D9890!=((current->mutation&16)?0xA7:(current->old&&(current->mutation&2))?0x5A:current->state))return 1;
 for(i=0;i<10;i++)if(((void**)D_800D9898)[i]!=expected[i])return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(bad):pre+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 pre+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return pre,dict(cases_per_profile=len(rows),negative_controls=len(bad),defined_descriptor_bytes=40,unwritten_padding_claimed=False,private_stack_aliases_claimed=False,all_ten_slots_and_untouched_neighbors=True,signed_word_to_float32_rounding=True,old_pointer_capture_live_helpers_and_return_store=True)

def run_native(selected):
 text,counts=harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=counts['cases_per_profile'],UBSan=True)
 return dict(profiles=reports,**counts)

def compiled_controls(selected):
 headers,body=selected.split('/* Replace',1);body='/* Replace'+body;results={}
 for name,source in controls(body).items():
  obj,diag=compile_owner(r,o,headers+source,'control-'+name);assert not diag,diag;words=oracle.linked(obj,'linked-control-'+name);witness=None
  for c in oracle.cases():
   initial=oracle.fixture(c);m=oracle.Oracle(words,initial,c);m.run()
   try:oracle.verify(m,initial,c)
   except AssertionError:witness=dict(x=c.x,slot=c.slot,old=c.old,result=c.result,mutation=c.mutation);break
  assert witness is not None,('ineffective compiled control',name);results[name]=witness
 return dict(count=len(results),semantic_witnesses=results,compiler_or_oracle_errors_accepted=False)
