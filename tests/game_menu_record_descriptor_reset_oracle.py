"""Menu descriptor reset: captured old pointer, defined fields and original factory chain."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
r=Path.cwd();o=r/'conker/build/game-menu-record-descriptor-reset-match';F='func_150B7484';ENTRY=0x150B7484;BODY=220;OLD=0x30000;OUTPUT=0x40000
SYMS=dict(D_800D9898=0x800D9898,D_800D9890=0x800D9890,D_800918DC=0x800918DC,func_1516972C=0x1516972C,func_15169968=0x15169968)
CTOR,ALLOC,COPY=0x15169900,0x15167A68,0x10023A10
@dataclass(frozen=True)
class Case:
 old:int=OLD
 result:int=OUTPUT
 state:int=37
 mutation:int=0
 phase:int=0
 seed:int=0
 connected:int=0

def packet(c):return STACK+c.phase-60
def fields(s=SYMS):
 return [(0,s['D_800918DC'],4),(0x14,0,2),(0x16,0,2),(0x18,0,2),(0x1C,0x42700000,4),(0x20,0x42700000,4),(0x24,0,2),(0x26,0,2),(0x28,81,2),(0x2A,81,2),(0x2C,88,2),(0x2E,88,2),*( (0x30+i,v,1)for i,v in enumerate((6,1,255,0,0,255,7,21,1,0)))]
DEFINED=tuple(sorted({p+i for p,v,n in fields()for i in range(n)}));assert len(DEFINED)==40
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
 for base in(OLD,OUTPUT,0x50000):m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(128)})
 for p in(s['D_800D9898'],s['D_800D9890']):m.update({p+i:(i*13+c.seed+0x63)&255 for i in range(-8,12)})
 put(m,s['D_800D9898'],c.old);m[s['D_800D9890']]=c.state
 return m
def release_effect(m,c,s=SYMS):
 if c.mutation&1:put(m,s['D_800D9898'],0x50000)
 if c.mutation&2:m[s['D_800D9890']]=0x5A
 # A private-stack perturbation is deliberately guest-only: the destructor
 # does not receive this pointer in portable native C.
 if c.mutation&4:put(m,packet(c)+0x14,0xFEDC,2);m[packet(c)+7]^=0x55
def create_effect(m,c,s=SYMS):
 if c.mutation&8:put(m,packet(c)+0x14,99,2);m[packet(c)+7]^=0xA5
 if c.mutation&16:put(m,s['D_800D9898'],0x50000);m[s['D_800D9890']]=0xA7
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def reference(initial,c,s=SYMS):
 m=dict(initial);old=read(m,s['D_800D9898']);p=packet(c);calls=[];obs=[]
 for at,v,n in fields(s):put(m,p+at,v,n)
 if old:calls.append((s['func_1516972C'],(old,)));release_effect(m,c,s)
 calls.append((s['func_15169968'],(p,)));obs.append((data(m,p,60),read(m,s['D_800D9898']),m[s['D_800D9890']]))
 if c.connected:calls.extend(((CTOR,(p,255)),(ALLOC,(94,0,76,0,255,1))))
 create_effect(m,c,s)
 if c.connected and c.result:
  calls.append((COPY,(p,c.result+16,60)));copied=data(m,p,60)
  for i,b in enumerate(copied):m[c.result+16+i]=b
 put(m,s['D_800D9898'],c.result);m[s['D_800D9890']]=3
 return m,calls,obs
def cases():
 rows=[Case(old,result,state,mu,phase,seed)for old,result,state,mu,phase,seed in itertools.product((0,OLD,0xFFFFFFFF),(0,OUTPUT,0x80000000),(0,1,128,255),(0,1,2,3,4,8,16,31),(0,8),(0,113))]
 rows.extend(Case(old,result,byte,phase=phase,seed=byte%3)for byte,old,result,phase in itertools.product(range(256),(0,OLD),(0,OUTPUT),(0,8)))
 return tuple(dict.fromkeys(rows))
def native_safe(c):return c.old in(0,OLD)and c.result in(0,OUTPUT)and not(c.mutation&4)and not c.phase
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.descriptor_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.before=self.r[:]
 def record_call(self,t):
  counts={self.syms['func_1516972C']:1,self.syms['func_15169968']:1,CTOR:2,ALLOC:6,COPY:3,ENTRY:0};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_15169968']:self.descriptor_observations.append((data(self.memory,a[0],60),read(self.memory,self.syms['D_800D9898']),self.memory[self.syms['D_800D9890']]))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  if t==s['func_1516972C']:release_effect(self.memory,c,s);value=0xDEADBEEF
  elif t in(s['func_15169968'],ALLOC):
   if t==s['func_15169968']:assert a==(packet(c),)
   else:assert a==(94,0,76,0,255,1)
   create_effect(self.memory,c,s);value=c.result
  else:
   assert t==COPY and a==(packet(c),c.result+16,60),(t,a);copied=data(self.memory,a[0],a[2])
   for i,b in enumerate(copied):self.memory[a[1]+i]=b
   value=0xAABBCCDD
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value&0xFFFFFFFF
def linked(obj,label,s=SYMS,entry=ENTRY):
 from tools.experiments.alternative_source_draft_word_screen import emit_function
 from tools.pad_generated_object import parse_object
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.descriptor_observations)
def verify(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.descriptor_observations)==(public(want),calls,obs),c
 assert data(m.memory,packet(c),60)==data(want,packet(c),60),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:
   m=Oracle(words,initial,c);m.before_f=m.f[:];m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(),Case(old=0),Case(result=0,mutation=31),Case(old=0xFFFFFFFF,result=0x80000000,mutation=8,phase=8)):
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
  s=dict(D_800D9898=0x80007FF0+k*0x100000,D_800D9890=0x80018000+k*0x100000,D_800918DC=0x8002FFF0+k*0x100000,func_1516972C=0x10008000+k*0x10000,func_15169968=0x10018000+k*0x10000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for old,result,mu,phase in itertools.product((0,OLD),(0,OUTPUT),(0,3,8,31),(0,8)):
   c=Case(old,result,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in programs:m=Oracle(words,initial,c,s,entry);m.before_f=m.f[:];m.run();verify(m,initial,c,s)
   rebased+=1
 aliases=0
 for field,at,old,result,mu,phase in itertools.product(('D_800D9898','D_800D9890'),(0,0x14,0x2C),(0,OLD),(0,OUTPUT),(0,3,8,31),(0,8)):
  c=Case(old,result,mutation=mu,phase=phase);s=dict(SYMS);s[field]=packet(c)+at;initial=fixture(c,s);programs=[linked(p,'alias-'+str(aliases)+'-'+str(i),s)for i,p in enumerate(objects)];machines=[]
  for words in programs:m=Oracle(words,initial,c,s);m.before_f=m.f[:];m.run();verify(m,initial,c,s);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helpers={}
 for entry,off,n in((CTOR,0x196DB0,26),(SYMS['func_15169968'],0x196E18,8)):helpers.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 connected_count=0
 for old,result,mu,phase in itertools.product((0,OLD),(0,OUTPUT),(0,1,2,3,4,8,16,31),(0,8)):
  c=Case(old,result,mutation=mu,phase=phase,connected=1);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c,connected=helpers);m.before_f=m.f[:];m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 pc=0x150B6C28;window=list(struct.unpack_from('>2I',rom,0xE40D8));assert window==[0x0D42DD21,0];caller_count=0
 for old,result,mu,phase in itertools.product((0,OLD),(0,OUTPUT),(0,3,8,31),(0,8)):
  c=Case(old,result,mutation=mu,phase=phase);initial=fixture(c);want,calls,obs=reference(initial,c)
  for words in ps:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[pc+8]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(pc+8,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.descriptor_observations)==(public(want),[(ENTRY,())]+calls,obs)
  caller_count+=1
 return dict(cases=count,executions=count*3,covered_words=len(visited),compiler_words=55,frame=88,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_stack_global_alias_cases=aliases,original_factory_helper_words=34,connected_factory_cases=connected_count,original_caller_window_cases=caller_count,original_caller_window=dict(entry=hex(pc),ROM='0xE40D8',words=2,argument_count=0,result_ignored=True,full_parent_claimed=False),descriptor_bytes=60,defined_descriptor_bytes=40,unwritten_descriptor_bytes=20,literal_full_state_equal=True,private_only=True,installed=False,matching_credit=0)

import sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
q=sys.modules[__name__]
def controls(body):
 return dict(inverted_release=body.replace('!= NULL','== NULL'),wrong_asset=body.replace('descriptor.asset = D_800918DC','descriptor.asset = D_800918DC + 4'),wrong_float=body.replace('60.0f','59.0f'),wrong_size=body.replace('= 88;','= 87;'),wrong_parameter=body.replace('= 21;','= 20;'),wrong_state=body.replace('D_800D9890 = 3','D_800D9890 = 2'),discarded_factory_result=body.replace('*(void **)D_800D9898 = func_15169968(&descriptor);','func_15169968(&descriptor);'),cleared_before_create=body.replace('*(void **)D_800D9898 = func_15169968(&descriptor);','*(void **)D_800D9898 = NULL;\n    *(void **)D_800D9898 = func_15169968(&descriptor);'),early_state=body.replace('    D_800D9890 = 3;','').replace('    descriptor.field31 = 1;','    D_800D9890 = 3;\n    descriptor.field31 = 1;'))

def native_harness(selected):
 declaration=selected[selected.index('typedef struct'):selected.index('/* Replace')];body=selected[selected.index('/* Replace'):];bad=controls(body);assert all(t!=body for t in bad.values())
 pre='#include <ultra64.h>\n'+declaration+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(MenuRecordDescriptorE4070)==60,"descriptor");
_Static_assert(__builtin_offsetof(MenuRecordDescriptorE4070,field14)==0x14,"field14");
_Static_assert(__builtin_offsetof(MenuRecordDescriptorE4070,field1C)==0x1C,"field1C");
_Static_assert(__builtin_offsetof(MenuRecordDescriptorE4070,field39)==0x39,"field39");
u8 D_800D9898[8] __attribute__((aligned(8))),D_800D9890,D_800918DC[12];
static u8 oldObject[128],newObject[128],otherObject[128];
typedef struct {u32 old,result,state,mutation;} Fixture;
static const Fixture *current;static u32 released,created,bad;
static void* pointer(u32 id){return id==0x30000?oldObject:id==0x40000?newObject:id==0x50000?otherObject:0;}
static u32 canonical(void*p){return p==oldObject?0x30000:p==newObject?0x40000:p==otherObject?0x50000:p?0xDEADBEEF:0;}
void func_1516972C(void *p){if(!p||canonical(p)!=current->old||released||created)bad=1;released++;
 if(current->mutation&1)*(void**)D_800D9898=otherObject;if(current->mutation&2)D_800D9890=0x5A;}
void *func_15169900(void *packet,s32 priority){MenuRecordDescriptorE4070*d=packet;u32 expectedOld=current->old,expectedState=current->state;
 if(current->old){if(current->mutation&1)expectedOld=0x50000;if(current->mutation&2)expectedState=0x5A;}
 if(priority!=255||created||released!=(current->old?1u:0u)||canonical(*(void**)D_800D9898)!=expectedOld||D_800D9890!=expectedState)bad=2;
 if(d->asset!=D_800918DC||d->field14||d->field16||d->field18||d->field1C!=60.0f||d->field20!=60.0f||d->field24||d->field26||d->field28!=81||d->field2A!=81||d->field2C!=88||d->field2E!=88||d->field30!=6||d->field31!=1||d->field32!=255||d->field33||d->field34||d->field35!=255||d->field36!=7||d->field37!=21||d->field38!=1||d->field39)bad=3;
 created++;if(current->mutation&8){d->field14=99;d->reserved04[3]=0xA5;}if(current->mutation&16){*(void**)D_800D9898=otherObject;D_800D9890=0xA7;}
 return pointer(current->result);}
'''
 # This is the repaired wrapper's exact C body. Its provider boundary is
 # intentionally opaque in native tests; both original factory bodies run
 # in the connected guest cases.
 pre+='void *func_15169968(register void *arg0) { return func_15169900(arg0, 0xFF); }\n'
 pre+='\n'.join(t.replace('func_150B7484','test_'+name)for name,t in dict(selected=body,**bad).items())
 rows=[]
 for c in q.cases():
  if q.native_safe(c):rows.append('{0x%Xu,0x%Xu,%d,%d}'%(c.old,c.result,c.state,c.mutation))
 pre+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 pre+=r'''
typedef void(*Fn)(void);
static s32 check(Fn fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;released=created=bad=0;for(i=0;i<8;i++)D_800D9898[i]=0xA5;*(void**)D_800D9898=pointer(current->old);D_800D9890=(u8)current->state;fn();
 if(bad||created!=1||released!=(current->old?1u:0u)||canonical(*(void**)D_800D9898)!=current->result||D_800D9890!=3)return 1;for(i=4;i<8;i++)if(D_800D9898[i]!=0xA5)return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(bad):pre+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 pre+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return pre,dict(cases=len(rows),negative_controls=len(bad),defined_descriptor_bytes=40,unwritten_descriptor_bytes_claimed=False,private_destructor_stack_mutations_claimed=False,wrapper_C_body_executed=True)

def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
