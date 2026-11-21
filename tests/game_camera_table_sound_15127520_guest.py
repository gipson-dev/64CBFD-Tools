"""Independent table-sound model; raw scheduling and guarded fault order differ."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,sys
from tools.experiments import game_camera_table_sound_15127520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import test_game_actor_burst_consumer_match as faults
ENTRY,RELEASE,EMIT,EVENT,TABLE,FACTOR=0x15127520,0x100111C8,0x10010F30,0x151CC290,0x800894E0,0x800A3580
SLOT,CAMERA,PRIMARY,SECONDARY,STATE,AUX,MARK=0x30000,0x40000,0x50000,0x51000,0x60000,0x70000,0x71000
SYMS={'D_800894E0':TABLE,'D_800A3580':FACTOR,'func_100111C8':RELEASE,'func_10010F30':EMIT,'func_151CC290':EVENT}
ROWS=((0x603,0x604,0x605),(0x620,0x621,0x622))
@dataclass(frozen=True)
class Case:
 phase:int=0;mode:int=2;selector:int=0;delta:int=0;kind:int=0;handle:int=9;flags:int=0x80;mutation:int=0;alias:int=0;profile:int=0
 value:int=0xBF000000;factor:int=0xC61C4000;fcsr:int=0;x:int=0x42CA8000;y:int=0xC1A20000;z:int=0x3E000000;state_pointer:int=0
def state_address(c):return c.state_pointer or(STATE,SLOT+0x24,SLOT+2,SLOT+4,SLOT+6,SLOT,TABLE+6*c.selector,TABLE+6*c.selector+2,TABLE+6*c.selector+4)[c.alias]
def rows(c):return ROWS if not c.profile else((0x8000,0xFFFF,0),(0,0x8001,0xFEFF))
def converted(value):
 if not math.isfinite(value):return 0xFFFFFFFF
 n=math.trunc(value);return n if 0<=n<2**32 else 0xFFFFFFFF
def product(c):return float32(floating(c.value)*floating(c.factor))
def args(c):return(SLOT,*(AUX+i*16 for i in range(5)),state_address(c))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((SLOT-16,80),(CAMERA,0x900),(PRIMARY,0x340),(SECONDARY,0x340),(STATE,8),(AUX,80),(MARK,16),(TABLE,12)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 for i,row in enumerate(rows(c)):
  for j,v in enumerate(row):put(m,TABLE+6*i+2*j,v,2)
 put(m,SLOT+0x18,CAMERA);put(m,SLOT+0x1C,(c.selector<<31)|((converted(product(c))+c.delta)&0xFFFFFF))
 put(m,SLOT+0x24,c.handle,2);put(m,SLOT+0x10,c.flags);put(m,CAMERA+0x3D0,PRIMARY);put(m,CAMERA+0x3D4,SECONDARY)
 for at,v in((0x14,c.x),(0x18,c.y),(0x1C,c.z)):put(m,PRIMARY+at,v)
 put(m,CAMERA+0x1A4,c.value);m[SECONDARY+0x197]=c.mode;put(m,FACTOR,c.factor)
 row=rows(c)[c.selector];pending=(0,row[0],row[1],row[2],0xFFFF)[c.kind];put(m,state_address(c),pending,2)
 return m
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+1024}
def effect(m,c,target):
 put(m,MARK,read(m,MARK)^target)
 if not c.mutation:return
 row=TABLE+6*c.selector
 for i,mask in enumerate((0x40,0x80,0x100)):put(m,row+2*i,read(m,row+2*i,2)^mask,2)
 put(m,SLOT+0x10,read(m,SLOT+0x10)^0x180)
 if target==RELEASE:put(m,SLOT+0x24,0xBEEF,2);put(m,state_address(c),0x3333,2)
def reference(initial,c,include_stack=False):
 m=dict(initial);calls=[];camera=read(m,SLOT+0x18);packed=read(m,SLOT+0x1C);selector=packed>>31;prior=packed&0xFFFFFF
 row=TABLE+6*selector;pending=state_address(c);scaled=float32(floating(read(m,camera+0x1A4))*floating(read(m,FACTOR)))
 if read(m,pending,2)==read(m,row+4,2):put(m,pending,0,2)
 for at,to in((0x14,2),(0x18,4),(0x1C,6)):put(m,SLOT+to,int(floating(read(m,read(m,camera+0x3D0)+at))),2)
 if m[read(m,camera+0x3D4)+0x197]!=2:return(m if include_stack else public(m,c)),calls,1
 now=converted(scaled);changed=prior!=now
 if changed:put(m,SLOT+0x1C,(selector<<31)|now)
 def call(target,a):calls.append((target,a));effect(m,c,target)
 def release():
  handle=read(m,SLOT+0x24,2)
  if handle:call(RELEASE,(handle,))
 if changed:
  if read(m,pending,2)!=read(m,row,2):
   release();put(m,SLOT+0x24,0,2);put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80);put(m,pending,read(m,row,2),2)
 elif read(m,pending,2)==read(m,row,2):
  release();put(m,SLOT+0x24,0,2);put(m,pending,read(m,row+2,2),2);call(EMIT,(read(m,row+2,2),20000,64,0,0));put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80)
 elif read(m,SLOT+0x10)&0x80:
  call(EVENT,(camera,));call(EMIT,(read(m,row+4,2),20000,64,0,0))
 put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80)
 return(m if include_stack else public(m,c)),calls,0
class Machine(FactoryOracle):
 def __init__(self,words,c,m):
  self.c=c;self.annotated=[];self.fcsr=c.fcsr
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=args(c));self.fcsr=c.fcsr
 def execute(self,w):
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,w)
  else:super().execute(w)
 def get(self,p,n):
  value=super().get(p,n)
  if self.own_instruction:self.annotated.append((self.current_pc,('R',p,n,value)))
  return value
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.annotated.append((self.current_pc,('W',p,n,v&((1<<(8*n))-1))))
 def record_call(self,t):
  assert self.fcsr==self.c.fcsr,('FCSR leaked',hex(t),self.fcsr,self.c.fcsr)
  counts={RELEASE:1,EMIT:5,EVENT:1};assert t in counts,hex(t)
  a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def canonical(m,raw=False):
 mapping={128:129,129:128,147:150,150:147}if raw else{}
 result=[];segment=[]
 def flush():
  result.extend(event for _,event in sorted(segment,key=lambda pair:pair[0]));segment.clear()
 for pc,event in m.annotated:
  if ENTRY<=pc<ENTRY+656:segment.append((ENTRY+4*mapping.get((pc-ENTRY)//4,(pc-ENTRY)//4),event))
  else:flush();result.append(event)
 flush();return result
def programs():return[bound_blob(*payload(p,'func_15127520'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def reachable(words):
 pending=[0];seen=set();result=set()
 while pending:
  i=pending.pop()
  if i in seen:continue
  assert 0<=i<len(words);seen.add(i);result.add(i);w=words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op in(1,4,5,20,21):
   always=rs==rt and op in(4,20);never=rs==rt and op in(5,21)
   if not never:result.add(i+1);pending.append(i+1+(((w&65535)^32768)-32768))
   if not always:
    if op not in(20,21):result.add(i+1)
    pending.append(i+2)
  elif op==3:result.add(i+1);pending.append(i+2)
  elif op==0 and w&63==8:assert rs==31;result.add(i+1)
  else:pending.append(i+1)
 return result
def corpus():
 for mode,selector,kind,delta,handle,flags,mutation,phase in itertools.product((0,2),(0,1),range(5),(0,1),(0,9),(0,0x80),(0,1),(0,8)):
  yield Case(mode=mode,selector=selector,kind=kind,delta=delta,handle=handle,flags=flags,mutation=mutation,phase=phase)
 values=(0,0x80000000,bits(1),bits(42),bits(2**24),bits(2**31),bits(2**32-256),bits(2**32),bits(-.5),bits(-1),0x7FC12345,0x7F800000,0x7F7FFFFF)
 for value,selector,kind,delta,fcsr in itertools.product(values,(0,1),(0,1,3),(0,1),(0,0xA5A50003)):
  yield Case(value=value,factor=bits(1),selector=selector,kind=kind,delta=delta,fcsr=fcsr)
 for mode,selector in itertools.product(range(256),(0,1)):yield Case(mode=mode,selector=selector,kind=3,delta=1)
 for alias,kind,selector,mutation,profile in itertools.product(range(9),range(5),(0,1),(0,1),(0,1)):
  yield Case(alias=alias,kind=kind,selector=selector,mutation=mutation,profile=profile,delta=1)
def run():
 streams=programs();assert streams[0]==streams[2]and streams[0]!=streams[1];coverage=set();count=0
 for c in corpus():
  initial=fixture(c);expected=reference(initial,c);states=[]
  for i,words in enumerate(streams):
   m=Machine(words,c,dict(initial)).run();assert(public(m.memory,c),m.calls,m.r[2])==expected,c;assert m.fcsr==c.fcsr
   assert [v for _,v in m.annotated]==m.trace
   states.append((m.memory,canonical(m,i==1),m.calls,m.r[2],tuple(m.r[n]for n in(*range(16,24),28,29,30,31)),tuple(m.f[20:]),m.fcsr))
   coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+656)
  assert states[0]==states[1]==states[2],c;count+=1
 expected_reachable=reachable(streams[0]);assert set(range(164))-expected_reachable=={80,137}
 assert coverage==expected_reachable,sorted(expected_reachable-coverage)
 cuts=0
 for c in(Case(kind=1),Case(delta=1,mutation=1),Case(value=bits(2**31),factor=bits(1)),Case(alias=1,kind=3)):
  initial=fixture(c);limit=Machine(streams[0],c,dict(initial)).run().all_accesses
  for cut in range(limit):
   states=[]
   for words in(streams[0],streams[2]):
    m=Machine(words,c,dict(initial));m.cut=cut
    try:m.run();raise AssertionError('missing access boundary')
    except faults.AccessBoundary:pass
    states.append((m.memory,m.trace,m.calls,m.current_pc,m.delay_of,m.fcsr))
   assert states[0]==states[1],(c,cut);cuts+=1
 controls=[]
 for index,mask in((23,2),(125,1),(145,1),(155,0x40)):
  bad=list(streams[0]);bad[index]^=mask;failures=0
  for c in(Case(kind=1),Case(kind=3),Case(delta=1),Case(kind=0,flags=0xC0)):
   initial=fixture(c)
   try:m=Machine(bad,c,dict(initial)).run();failed=(public(m.memory,c),m.calls,m.r[2])!=reference(initial,c)
   except(AssertionError,KeyError):failed=True
   failures+=failed
  assert failures,index;controls.append({'word':index,'failures':failures})
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':[80,137],'all_164_guarded_words_identical':True,
  'retail_padded_fault_prefixes':cuts,'raw_fault_order_claim':False,'raw_trace_normalizes_only_declared_scheduling_words':[128,129,147,150],
  'bounded_explicit_FCSR_control_model':True,'effective_controls':controls,'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
