"""Independent phase semantics, actual request relay and indirect callback windows."""
from dataclasses import dataclass,replace
import itertools,json,math,struct
from tools.experiments import game_owner_phase_update_150bf760_match as checkpoint
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_animation_timeline_oracle import bits as pack,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
r,o=checkpoint.ROOT,checkpoint.OUT;ENTRY=0x150BF760;OWNER=0x30000;OBJECT=0x50000;ANIMATION=0x51000;TABLE=0x53000;MARK=0x55000;SCRIPT=0x56000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};CONSTANTS=checkpoint.MANIFEST['constants']
u32=lambda n:n&0xFFFFFFFF
def bits(v):return 0x7FC00000 if math.isnan(v)else pack(v)
def calc(a,b,op):
 x,y=floating(a),floating(b)
 if op=='/':v=x/y if y else math.nan if not x or math.isnan(x)else math.copysign(math.inf,x*math.copysign(1.,y))
 else:v={'+':lambda:x+y,'-':lambda:x-y,'*':lambda:x*y}[op]()
 return bits(v)
class GuestFault(Exception):pass
@dataclass(frozen=True)
class Case:
 phase:int=0
 owner:int=OWNER
 stack_phase:int=0
 numerator:int=0x40000000
 duration:int=0x41200000
 present:int=1
 created:int=1
 handle:int=0
 state:int=0
 mutation:int=0
 gate:int=0
 index:int=0
 sine:int=0x3EAAAAAB
 result:int=0x89ABCDEF
 zero_page:int=0
 seed:int=0
def cases():
 values=(0,0x80000000,0x3FFFFFFF,0x40000000,0x40000001,0x40BFFFFF,0x40C00000,0x40C00001,0x40FFFFFF,0x41000000,0x41000001,0xC1000000,1,0x7F800000,0xFF800000,0x7FC12345)
 for i,v in enumerate(itertools.product(range(4),(0,1),(0,1),(0,0x92345678),(0,1),(0,8),(0,2,3),range(4))):
  phase,present,created,handle,mutation,stack_phase,state,gate=v
  yield Case(phase=phase,owner=OWNER if i&1 else STACK+128,stack_phase=stack_phase,numerator=values[(i//3)%len(values)],present=present,created=created,handle=handle,state=state,mutation=mutation,gate=gate,index=(-1,0,2)[i%3],sine=(0,0x80000000,0x3F800000,0xBF800000,0x3EAAAAAB,1,0x7F800000,0x7FC12345)[i%8],seed=i)
 for phase,numerator,duration in itertools.product(range(4),(0,0x3F800000,0xBF800000),(0x40000000,0x7F800000,0x7FC12345)):
  yield Case(phase=phase,numerator=numerator,duration=duration,seed=13)
 for phase,state,mutation in itertools.product((1,2),(0,3),(0,1)):
  yield Case(phase=phase,present=0,created=0,zero_page=1,state=state,mutation=mutation,seed=7)
def fixture(c=Case(),s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for p,n in((OWNER-32,0x240),(OBJECT-32,0x340),(ANIMATION,32),(TABLE-96,336),(MARK,32),(SCRIPT,32)):
  m.update({p+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 if c.zero_page:m.update({p:(p*7+c.seed)&255 for p in range(0x200,0x240)});m[0x232]=c.state;put(m,0x218,0x87654321)
 put(m,c.owner+0x1C,0x63000000+c.seed);put(m,c.owner+0x124,c.handle);put(m,c.owner+0xA8,0x42C60000);m[c.owner+0x73]=(c.seed*4&0xFC)|c.phase
 m[OBJECT+0x232]=c.state;put(m,OBJECT+0x218,0x87654321);put(m,OBJECT+0x2D0,ANIMATION);put(m,ANIMATION+8,c.numerator);put(m,ANIMATION+0x18,c.duration)
 for name,value in CONSTANTS.items():put(m,s[name],value)
 put(m,s['D_800902B8'],0x12345678);put(m,s['D_800D20FC'],TABLE)
 for name,v in zip(('D_800C35EA','D_800C35E8'),((0,0),(1,0),(1,1),(2,255))[c.gate]):m[s[name]]=v
 return m
def effect(memory,c,kind,s):
 put(memory,MARK+4*kind,0x13570000+kind)
 if c.mutation and kind==0:
  memory[c.owner+0x73]^=1;put(memory,c.owner+0x124,0);put(memory,c.owner+0x1C,0xABCD0000|c.seed&65535);put(memory,s['D_800902B8'],0x76543210)
 if c.mutation and kind==1:memory[OBJECT+0x232]^=3
def reference(initial,c=Case(),s=None):
 s=S if s is None else s;m=initial.copy();calls=[];fault=None
 def call(name,args,kind=None):
  calls.append((s[name],tuple(map(u32,args))))
  if kind is not None:effect(m,c,kind,s)
 if m[s['D_800C35EA']]==1 and m[s['D_800C35E8']]!=1:return m,calls,fault
 call('func_1511B51C',(c.owner,),0)
 if read(m,c.owner+0x124)==0:
  a=(c.owner,read(m,s['D_800902B8']),1,0xFFFFFFFF,0,0,0xFFFFFFF8);call('func_15195FB0',a);call('func_15195DD4',(read(m,c.owner+0x1C),*a[1:]),2);put(m,c.owner+0x124,c.result)
 call('func_15083E90',(20,));obj=OBJECT if c.present else 0;phase=m[c.owner+0x73]&3;progress=calc(c.numerator,calc(c.duration,0x40000000,'-'),'/')if obj else 0;put(m,c.owner+0xA8,0)
 if phase==2 and floating(progress)<=0.75:
  arg=calc(calc(progress,read(m,s['D_800A0124']),'*'),read(m,s['D_800A0128']),'*');call('sinf',(arg,),1);put(m,c.owner+0xA8,calc(c.sine^0x80000000,0x41200000,'*'))
 elif phase in(0,1)and floating(progress)>=0.25:
  factor=read(m,s['D_800A012C'if phase==0 else'D_800A0130']);arg=calc(calc(progress,factor,'*'),factor,'-');call('sinf',(arg,),1);put(m,c.owner+0xA8,calc(c.sine,0x41200000,'*'))
 if phase in(1,2):
  if not obj:
   call('func_15083E0C',(20,));m[read(m,s['D_800D20FC'])+c.index*48+2]=0;call('func_150825C0',(c.index,0),3);call('func_15083E90',(20,));obj=OBJECT if c.created else 0
  if phase==2 or not obj:
   address=obj+0x232
   if address not in m:return m,calls,(address,1)
   value=2 if phase==2 else 3
   if m[address]!=value:m[address]=value;put(m,obj+0x218,0)
 elif obj and floating(progress)>=1.0:call('func_15060F28',(obj,0),4)
 return m,calls,fault
class Oracle(Base):
 def __init__(self,words,initial,c=Case(),entry=ENTRY,extra=None,s=None):
  self.c=c;self.s=S if s is None else s;self.lookup_count=0;self.fault=None
  helper=bound_blob(*payload(o/'original-provider.o','func_15195FB0'),self.s);connected=dict(zip(range(self.s['func_15195FB0'],self.s['func_15195FB0']+64,4),helper));connected.update(extra or{})
  super().__init__(words,initial.copy(),BaseCase(phase=c.stack_phase),entry=entry,s={},connected=connected,arguments=(c.owner,))
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3,7):
   if fn==7:self.f[fd]=self.f[fs]^0x80000000
   else:self.f[fd]=calc(self.f[fs],self.f[ft],{0:'+',1:'-',2:'*',3:'/'}[fn])
  else:super().execute(w)
 def get(self,p,n):
  if any(p+i not in self.memory for i in range(n)):
   self.access();self.fault=(p,n);raise GuestFault(p,n)
  return super().get(p,n)
 def record_call(self,target):
  counts={'func_1511B51C':1,'func_15195FB0':7,'func_15195DD4':7,'func_15083E90':1,'func_15083E0C':1,'func_150825C0':2,'func_15060F28':2};by_address={self.s[n]:n for n in counts}
  if target==self.s['sinf']:args=(self.f[12],)
  elif target==ENTRY:args=(self.r[4],)
  else:assert target in by_address,hex(target);args=tuple(map(u32,self.arguments(counts[by_address[target]])))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  names={self.s[n]:n for n in('func_1511B51C','func_15195DD4','func_15083E90','func_15083E0C','func_150825C0','func_15060F28','sinf')};name=names[target];value=0xA5B61234
  if name=='func_1511B51C':effect(self.memory,self.c,0,self.s)
  elif name=='sinf':effect(self.memory,self.c,1,self.s)
  elif name=='func_15195DD4':effect(self.memory,self.c,2,self.s);value=self.c.result
  elif name=='func_15083E90':value=OBJECT if(self.c.present if self.lookup_count==0 else self.c.created)else 0;self.lookup_count+=1
  elif name=='func_15083E0C':value=u32(self.c.index)
  elif name=='func_150825C0':effect(self.memory,self.c,3,self.s)
  elif name=='func_15060F28':effect(self.memory,self.c,4,self.s)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
  if name=='sinf':self.f[0]=self.c.sine
def streams():return{label:bound_blob(*payload(o/path,'func_150BF760'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_EC420.c.o',retail='original-target.o').items()}
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.fault)
def run(m):
 try:m.run()
 except GuestFault:pass
 return m
def check(m,initial,c,s=None,caller=False):
 expected,calls,fault=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.calls==([(ENTRY,(c.owner,))]if caller else[])+calls,(c,m.calls,calls);assert m.fault==fault,(c,m.fault,fault)
 if not fault:assert m.r[16:24]==m.before[16:24]and m.r[28:31 if caller else 32]==m.before[28:31 if caller else 32]
def main():
 programs=streams();assert len({tuple(ws)for ws in programs.values()})==1;visits=set();count=faults=mapped=0
 for c in cases():
  initial=fixture(c);models=[run(Oracle(ws,initial,c))for ws in programs.values()];assert state(models[0])==state(models[1])==state(models[2])
  for m in models:check(m,initial,c)
  visits.update(models[0].visits);count+=1;faults+=models[0].fault is not None;mapped+=bool(c.zero_page)
 q=dict(cases_per_stream=count,streams=list(programs),complete_state_and_access_trace_equal=True,independent_public_semantics_equal=True,unmapped_null_fault_cases=faults,explicit_guest_only_zero_page_cases=mapped,unexecuted_target_words=[i for i in range(199)if ENTRY+4*i not in visits],actual_16_word_request_relay_connected=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Sine, resource, phase and object services are bounded providers. Zero-page mapping cases are guest-only controls; native C null dereferences and FCSR/hardware behavior are not qualified.');assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs=streams();count=0
 for c in(Case(phase=2,present=1),Case(phase=0,mutation=1,owner=STACK+128),Case(phase=1,present=0,created=0),Case(phase=1,present=0,created=0,zero_page=1)):
  initial=fixture(c);complete=run(Oracle(programs['retail'],initial,c))
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire before completion/fault')
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(raw_padded_retail_full_state_access_prefix_triples=count,includes_actual_relay_and_null_read_cut=True,source_installed=checkpoint.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();programs=streams();count=0
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rotable=0x80088C90;values=struct.unpack_from('>3I',elf,elf_slot_offset(elf,rotable+8*12,12));assert values==(ENTRY,0,0)
 setup=0x1509EBBC;setup_end=0x1509ED5C;setup_words=struct.unpack_from('>22I',rom,setup-0x15000000+0x2D4B0);setup_cases=0
 for c in(Case(),Case(owner=STACK+128),Case(owner=STACK+128,stack_phase=8)):
  initial=fixture(c);put(initial,SCRIPT+8,8)
  for i,v in enumerate(values):put(initial,rotable+8*12+4*i,v)
  expected=initial.copy();put(expected,c.owner+0x38,ENTRY);put(expected,c.owner+0x78,0);expected[c.owner+0x92]=0
  m=Oracle(setup_words,initial,c,entry=setup);m.r[2]=c.owner;m.r[16]=SCRIPT;m.code[setup_end]=0;m.code=WindowCode(m.code,m);m.code.ends=(setup_end,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Setup boundary missing')
  assert m.memory==expected and not m.calls;setup_cases+=1
 for entry,end in((0x15113EE0,0x15113EF0),(0x15113FB8,0x15113FC8)):
  words=struct.unpack_from('>4I',rom,entry-0x15000000+0x2D4B0)
  for c in list(cases())[::32]:
   initial=fixture(c);put(initial,c.owner+0x38,ENTRY);models=[]
   for ws in programs.values():
    m=Oracle(words,initial,c,entry=entry,extra=dict(zip(range(ENTRY,ENTRY+796,4),ws)));m.r[16]=c.owner;m.before=m.r[:];m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except(WindowBoundary,GuestFault):pass
    else:raise AssertionError('Caller boundary missing')
    check(m,initial,c,caller=True);models.append(m)
   assert state(models[0])==state(models[1])==state(models[2]);count+=1
 q=dict(real_table_setup_window_words=22,table_setup_cases=setup_cases,table_index=8,real_indirect_caller_windows=2,words_per_window=4,cases_per_stream=count,owner_pointer_and_discarded_result_verified=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Actual table-to-object setup and object-field JALR windows; complete dispatcher parents not executed.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
