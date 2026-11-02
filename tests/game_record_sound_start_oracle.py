"""Record sound-start access order, real audio enqueue and original caller windows."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
ENTRY,HELPER,CENTS,SORT=0x150A23E4,0x1000FA64,0x10019AB0,0x10011624
RECORD,TABLE,COUNT,OUTER=0x30000,0x80041FE0,0x80042760,0x800D3094
u32=lambda v:v&0xFFFFFFFF
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 selector:int=0
 flags:int=0
 state:int=0
 phase:int=0
 profile:int=0
 mutation:int=0
 queue:int=0
 sorting:int=0
 record:int=RECORD

def cases():
 result=[Case(s,f,state,phase,(s+f)%4,s>>6&3)for s,f,state,phase in itertools.product(range(256),(0,255),(0,0x80000000),(0,8))]
 result += [Case(s,f,0,0,f%4,f>>6&3)for s,f in itertools.product((0,128),range(256))]
 result += [Case(s,0,state,8,3,3)for s,state in itertools.product((0,127,128,255),(1,0x100,0x10000,0x7FFFFFFF,0xFFFFFFFF))]
 return result

def fixture(c):
 m={STACK+c.phase+i:(i*17+165)&255 for i in range(-2048,2048)}
 for base,size in((c.record-16,96),(TABLE-16,0x800),(COUNT-8,32),(OUTER-8,32)):
  m.update({base+i:(i*29+c.selector*13+90)&255 for i in range(size)})
 coords=((0,1,-1),(-32768,32767,-12345),(32767,-32768,12345),(-1,0,-32768))[c.profile]
 for i,v in enumerate(coords):put(m,c.record+2*i,v,2)
 m[c.record+0x15]=c.flags;m[c.record+0x17]=c.selector
 put(m,c.record+0x18,(0,0xFFFF0000,0xFEDC1234,0x80008000)[c.profile])
 put(m,c.record+0x1C,(0,0xFFFFFFFF,0x80007FFF,0xABCD8001)[c.profile]);put(m,c.record+0x20,c.state)
 put(m,COUNT,c.queue);put(m,OUTER,0x12345678)
 return m

def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-2048<=p<STACK+c.phase+2048}

def arguments(m,c):
 p=c.record;packed=read(m,p+0x1C);flags=read(m,p+0x18)|(0x8000 if m[p+0x15]&3==0 else 0)
 return (packed>>16,*[u32(half(read(m,p+2*i,2)))for i in range(3)],(m[p+0x17]&127)*327,flags,packed&65535,0,0,0,0x108 if m[p+0x17]&128 else 8,0)

def effect(m,c):
 if c.mutation&1:
  put(m,c.record+0x20,0xDEADBEEF);put(m,c.record+0x1C,0x13579BDF);m[c.record+0x15]^=255;m[c.record+0x17]^=255
 if c.mutation&2:
  for i in range(4):put(m,STACK+c.phase+4*i,0xABCDEF00+i)
  put(m,OUTER,9)

def reference(initial,c,connected=False):
 m=dict(initial);calls=[];observations=[]
 if read(m,c.record+0x20)==0:
  a=arguments(m,c);calls.append((HELPER,a));observations.append(0)
  if not connected:effect(m,c)
  elif c.queue<32:
   entry=TABLE+c.queue*48;put(m,COUNT,c.queue+1)
   for at,v,n in((0,a[0],2),(2,a[1],2),(4,a[2],2),(6,a[3],2),(8,a[5],2),(10,a[6],2),(12,a[4],4),(16,(a[10]&0x108)|2,4),(20,0,4),(24,0,4),(28,0,4),(32,0,2),(34,0,1),(35,0,1),(36,0,4),(40,0,2),(44,0x3F800000,4)):
    put(m,entry+at,v,n)
   calls.extend(((CENTS,(0,)),(SORT,(TABLE,COUNT,c.queue,c.queue+1))))
   effect(m,c)
   if c.sorting==1:put(m,COUNT,c.queue+2)
   elif c.sorting==2:put(m,entry+0x24,0xBEEF,2)
   if c.sorting!=1:put(m,entry+0x10,read(m,entry+0x10)|0x1000)
 put(m,c.record+0x20,1)
 return public(m,c),calls,observations

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,helper=HELPER,connected=None):
  self.c,self.helper=c,helper;self.observations=[]
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(c.record,))
 def record_call(self,t):
  counts={self.helper:12,CENTS:1,SORT:4,ENTRY:1};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((HELPER if t==self.helper else t,a))
  if t==self.helper:self.observations.append(read(self.memory,self.c.record+0x20))
 def hook(self,t):
  if t==self.helper:effect(self.memory,self.c);value=0xBEEF
  elif t==CENTS:effect(self.memory,self.c);value=0
  elif t==SORT:
   if self.c.sorting==1:put(self.memory,COUNT,self.c.queue+2)
   elif self.c.sorting==2:put(self.memory,TABLE+self.c.queue*48+0x24,0xBEEF,2)
   value=0
  else:raise AssertionError(hex(t))
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
  if t==CENTS:self.f[0]=0x3F800000

def programs(root,output,layout):
 entry=ENTRY+layout*0x1000000;helper=(HELPER,0x10027FFC,0x1003FFF8)[layout];roots=[]
 for label,obj,words in(('original',output/'original-func_150A23E4.o',55),('candidate',output/'flow-10.o',54)):
  p=output/('guest-layout-%d-%s'%(layout,label));p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%entry)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_150A23E4','--defsym=func_1000FA64=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
  image=p.with_suffix('.elf').read_bytes();at=elf_slot_offset(image,entry,words*4);roots.append(struct.unpack_from('>%dI'%words,image,at))
 return entry,helper,roots

def equivalent(a,b,c):
 assert public(a.memory,c)==public(b.memory,c) and a.r==b.r and a.f==b.f and a.calls==b.calls and a.trace==b.trace and a.observations==b.observations

def qualify(root,output):
 seen=[set(),set()];count=0
 for layout in range(3):
  entry,helper,roots=programs(root,output,layout)
  for c in cases():
   initial=fixture(c);expected,calls,obs=reference(initial,c);pair=[]
   for i,words in enumerate(roots):
    m=Oracle(words,initial,c,entry,helper).run();assert public(m.memory,c)==expected and m.calls==calls and m.observations==obs,(layout,c,m.calls,calls)
    seen[i].update(v-layout*0x1000000 for v in m.visits);pair.append(m);count+=1
   equivalent(*pair,c)
 entry,helper,roots=programs(root,output,0);prefixes=0
 for c in (Case(),Case(selector=255,flags=255,mutation=3,profile=3,phase=8),Case(state=0x100)):
  initial=fixture(c);complete=Oracle(roots[0],initial,c).run()
  for cut in range(complete.all_accesses):
   pair=[]
   for words in roots:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    pair.append(m)
   equivalent(*pair,c);prefixes+=1
 assert ENTRY+0xC4 not in seen[0] and ENTRY+0xC0 not in seen[1]
 report=dict(success=True,private_only=True,matching_credit=0,cases=len(cases())*3,executions=count,covered_original_words=len(seen[0]),covered_candidate_words=len(seen[1]),all_selector_and_flag_bytes=True,frame=64,original_words=55,candidate_words=54,access_prefix_pairs=prefixes,public_memory_GPR_FPR_calls_and_access_trace_equal=True,PC_and_delay_identity_claim=False,provider_record_and_incoming_home_mutations=True)
 return report

def helpers(root,output):
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes();retail=rom[0xFA64:0xFC18];at=elf_slot_offset(elf,HELPER,len(retail));assert elf[at:at+len(retail)]==retail
 symbols={n:f[1]for _,n,f,_ in symbol_rows(elf)};assert symbols['alCents2Ratio']==CENTS and symbols['func_10011624']==SORT
 code=dict(zip(range(HELPER,HELPER+len(retail),4),struct.unpack('>109I',retail)));entry,helper,roots=programs(root,output,0);seen=set();count=0
 for base in cases()[::41]:
  for queue,sorting in itertools.product((0,31,32,33),(0,1,2)):
   c=replace(base,queue=queue,sorting=sorting);initial=fixture(c);expected,calls,obs=reference(initial,c,True);pair=[]
   for words in roots:
    m=Oracle(words,initial,c,connected=code).run();assert public(m.memory,c)==expected and m.calls==calls and m.observations==obs,(c,m.calls,calls)
    seen.update(m.visits);pair.append(m);count+=1
   equivalent(*pair,c)
 return dict(success=True,cases=count//2,executions=count,original_helper_words=109,helper_words_covered=len(set(code)&seen),retained_helper_equals_original=True,queue_full_and_sort_count_mutation=True,all_root_results_ignored=True,lower_CENTS_and_SORT_mocked=True)

def callers(root,output):
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 rom=(root/'conker/conker.us.bin').read_bytes();entry,helper,roots=programs(root,output,0);reports=[]
 for start,end,n in((0x150A0AE4,0x150A0CDC,6),(0x150A1A48,0x150A1CF8,4)):
  window=struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0);count=0;seen=set()
  for c in cases()[::43]:
   initial=fixture(c);put(initial,0x800D3098,c.record-0x34);expected,calls,obs=reference(initial,c);pair=[]
   for words in roots:
    code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));code[end]=0;m=Oracle(window,initial,c,entry=start,connected=code)
    if start==0x150A0AE4:m.r[16]=0x34;m.r[17]=0x800D3098
    else:m.r[16]=c.record-0x34;m.r[3]=0x34
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    assert m.calls==[(ENTRY,(c.record,)),*calls] and public(m.memory,c)==expected and m.observations==obs,(hex(start),c,m.calls,calls)
    if start==0x150A0AE4:assert m.r[5]==read(expected,OUTER)
    pair.append(m);seen.update(m.visits);count+=1
   equivalent(*pair,c)
  assert set(range(start,start+n*4,4))<=seen
  reports.append(dict(window=hex(start),words=n,executions=count,all_window_words_executed=True))
 return dict(success=True,original_callers=2,windows=reports,parent_functions_still_unrecovered=True,full_parent_claim=False,result_not_consumed=True,following_global_count_reload_observed=True)
