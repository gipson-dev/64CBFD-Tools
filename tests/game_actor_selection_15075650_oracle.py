"""Independent byte-selection model, original RNG/flag helper and explicit trap prefixes."""
import itertools,json,struct,sys
from functools import lru_cache
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_actor_selection_15075650_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY,RANDOM,FLAGS,SEED=0x15075650,0x150ADA20,0x15075498,0x800885B0
ACTORS=(0x90000,0xA0000,0xB0000);TABLES=(0xC0000,0xC1000)
SYMS=dict(D_800D154C=0x800D154C,D_800D2108=0x800D2108,D_800D1890=0x800D1890,D_800D1891=0x800D1891,D_800D1892=0x800D1892,D_800D1893=0x800D1893,func_150ADA20=RANDOM,func_15075498=FLAGS)
@dataclass(frozen=True)
class Case:
 mode:int=254
 table:int=11
 override:int=0
 minimum:int=3
 current:int=3
 state:int=7
 timer:int=250
 rate:int=1
 flags:int=130
 random:int=6
 mutation:int=0
 real:bool=False
 seed:int=0x123456789ABCDEF0
 phase:int=0
 home_span:int=-1
 home_excluded:int=-1
 alias:int=0

def actor0(c,s):return s['D_800D154C']-0x44 if c.alias else ACTORS[0]
def actors(c,s):return(actor0(c,s),*ACTORS[1:],*((0x3F800000,)if c.alias else()))
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+165)&255 for i in range(-512,512)}
 for k,a in enumerate(actors(c,s)):
  m.update({a+i:(i*29+k*17+91)&255 for i in range(-16,828)})
  m[a+0x13F]=37;m[a+0x21F]=c.override;m[a+0x220]=c.minimum;m[a+0x21E]=c.current;m[a+0x223]=c.state;put(m,a+0x44,0x3F800000);put(m,a+0xF4,0xA5A5143E)
 for table in TABLES:m.update({table+i:(i*13+5)&255 for i in range(256)})
 m[TABLES[0]+37]=c.table;put(m,s['D_800D2108'],TABLES[0]);put(m,s['D_800D154C'],actor0(c,s));put(m,SEED,c.seed,8)
 for key,value in(('D_800D1890',c.timer),('D_800D1891',c.mode),('D_800D1892',c.rate),('D_800D1893',c.flags)):m[s[key]]=value
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def snapshot(m,c,s=SYMS):
 a=read(m,s['D_800D154C']);return(a,m[a+0x21E],m[a+0x220],m[a+0x223],read(m,a+0x21C,2),read(m,a+0x44),read(m,a+0xF4),read(m,a+0x244,2),read(m,SEED,8))
def effect(m,c,s):
 if c.mutation&1:
  put(m,s['D_800D154C'],ACTORS[1]);m[ACTORS[1]+0x220]=250;m[ACTORS[1]+0x21E]=2
 if c.mutation&2:m[s['D_800D1890']]=251;m[s['D_800D1892']]=1;m[s['D_800D1893']]=130
 if c.mutation&4:
  a=read(m,s['D_800D154C']);put(m,s['D_800D2108'],TABLES[1]);m[a+0x13F]=9;m[a+0x21F]=1;m[TABLES[1]+9]=3
def flag_model(m,s):
 a=lambda:read(m,s['D_800D154C']);flag=s['D_800D1893'];timer=s['D_800D1890']
 v=m[flag]&127
 if v!=127:put(m,a()+0x244,v,2)
 p=a()+0xF4;put(m,p,read(m,p)&~0x143E)
 if m[timer]==250:p=a()+0xF4;put(m,p,read(m,p)|0x22)
 elif m[timer]==251:p=a()+0xF4;put(m,p,read(m,p)|4)
 if m[flag]&128:p=a()+0xF4;put(m,p,read(m,p)|16)
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);calls=[];observations=[];a=lambda:read(m,s['D_800D154C']);p=a()
 upper=(m[read(m,s['D_800D2108'])+m[p+0x13F]]-1)&255
 if m[p+0x21F]:upper=m[p+0x21F]
 minimum=m[p+0x220];span=(upper-minimum)&255;mode=m[s['D_800D1891']]
 if mode in(254,255)and m[p+0x223]!=13:
  excluded=((upper if m[p+0x21E]<=minimum else m[p+0x21E])-1)&255
  calls.append((s['func_150ADA20'],()));observations.append(snapshot(m,c,s));effect(m,c,s)
  value=c.random
  if c.real:value=next_seed(read(m,SEED,8));put(m,SEED,value,8)
  if c.home_span>=0:span=c.home_span
  if c.home_excluded>=0:excluded=c.home_excluded
  if not span:return m,calls,observations,True
  selection=((value&0xFFFFFFFF)%span+m[a()+0x220])&255
  if mode==255 or selection!=excluded:m[a()+0x21E]=selection
 elif mode not in(254,255):m[p+0x21E]=mode
 m[a()+0x223]=0
 put(m,a()+0x21C,m[s['D_800D1890']]*100,2)
 rate=m[s['D_800D1892']]
 if rate!=255:
  put(m,a()+0x44,bits(float(rate)))
  if read(m,a()+0x44)==0x3F800000:put(m,a()+0x44,0x3F000000)
 p=a()
 if m[p+0x21E]<m[p+0x220]:m[p+0x21E]=m[p+0x220]
 calls.append((s['func_15075498'],()));observations.append(snapshot(m,c,s));flag_model(m,s)
 if c.mutation&8:put(m,s['D_800D154C'],ACTORS[2]);m[ACTORS[2]+0x223]=169
 return m,calls,observations,False
class TrapBoundary(Exception):pass
class Oracle(RngInstructions):
 def __init__(self,ws,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None,zero_pattern=0):
  self.zero_pattern=zero_pattern;self.observations=[]
  super().__init__(ws,memory,c,s,entry=entry,connected=connected,arguments=(0x87654321,));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def execute(self,w):
  if w==0x0007000D:raise TrapBoundary
  if w>>26==0 and w&63==27 and self.r[w>>16&31]&0xFFFFFFFF==0:
   self.hi=(0,self.r[w>>21&31]&0xFFFFFFFF,0xFFFFFFFF)[self.zero_pattern];self.lo=0xFFFFFFFF;return
  return super().execute(w)
 def record_call(self,t):
  assert t in(ENTRY,self.s['func_150ADA20'],self.s['func_15075498']),hex(t);self.calls.append((t,()));self.events.append(('CALL',t,()))
  if t==ENTRY:return
  self.observations.append(snapshot(self.memory,self.case,self.s))
  if t==self.s['func_150ADA20']:
   effect(self.memory,self.case,self.s);home=STACK+self.case.phase
   if self.case.home_span>=0:self.memory[home-1]=self.case.home_span
   if self.case.home_excluded>=0:self.memory[home-3]=self.case.home_excluded
 def hook(self,t):
  if t==self.s['func_150ADA20']:answer=self.case.random
  else:
   assert t==self.s['func_15075498'];flag_model(self.memory,self.s)
   if self.case.mutation&8:put(self.memory,self.s['D_800D154C'],ACTORS[2]);self.memory[ACTORS[2]+0x223]=169
   answer=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=answer&0xFFFFFFFF
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);a,n=fs['func_15075650']['value'],fs['func_15075650']['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
@lru_cache(maxsize=1)
def original_helpers():
 rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();result={}
 for entry,offset,n,name in((RANDOM,0xDAED0,18,'func_150ADA20'),(FLAGS,0xA2948,44,'func_15075498')):
  raw=rom[offset:offset+n*4];at=elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==raw,('Original helper not exact',name)
  result.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)))
 return result
def helper_code(c=Case(),s=SYMS):
 assert s['func_150ADA20']==RANDOM and s['func_15075498']==FLAGS
 return {p:w for p,w in original_helpers().items()if (c.real or not RANDOM<=p<RANDOM+72)and(not c.mutation&8 or not FLAGS<=p<FLAGS+176)}
def check(m,c=Case(),s=SYMS,trapped=False):
 want,calls,observations,trap=reference(m.initial,c,s)
 assert trap==trapped and(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),('selection public/call mismatch',c)
 if not trapped:assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 # Caller-owned homes beyond the four clobberable outgoing words stay intact.
 home=STACK+c.phase
 assert all(m.memory[p]==m.initial[p]for p in range(home,home+64)),('incoming homes',c)
def cases():
 result=[replace(Case(),mode=i,rate=i,timer=i,flags=i,phase=(i&1)*8)for i in range(256)]
 result +=[replace(Case(),mode=mode,rate=rate,timer=timer,flags=flags,state=state,random=value,minimum=minimum,current=current,table=table,override=override,phase=(value&1)*8)for mode,rate,timer,flags,state,value,(minimum,current,table,override)in itertools.product((254,255),(0,1,2,255),(0,250,251,255),(0,127,128,255),(0,13),(0,6,0x80000000,0xFFFFFFFF),((3,3,11,0),(250,252,3,0),(0,255,1,0),(7,6,99,9)))]
 result +=[replace(Case(),minimum=250,current=1,table=3,random=0xFFFFFFFF)]
 result +=[replace(Case(),mutation=i,random=v,mode=mode)for i,mode,v in itertools.product(range(16),(254,255),(0,6,0xFFFFFFFF))]
 result +=[replace(Case(),mode=mode,real=True,seed=seed)for mode,seed in itertools.product((254,255),SEEDS)]
 result +=[replace(Case(),mode=mode,home_span=span,home_excluded=excluded,mutation=1)for mode,span,excluded in itertools.product((254,255),(0,1,255),(-1,0,255))]
 result +=[replace(Case(),alias=1,mode=mode,rate=1,random=value)for mode,value in itertools.product((0,254,255),(0,6,0xFFFFFFFF))]
 return result
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_A28B0.c.o','retail':out/'retail-reference.o'};coverage={};counts={};total=traps=0;cs=cases()
 for label,path in paths.items():
  ws=words(path);seen=set();count=0
  for c in cs:
   expected=reference(fixture(c),c)[3]
   for zero in(range(3)if expected else(0,)):
    m=Oracle(ws,fixture(c),c,connected=helper_code(c),zero_pattern=zero);trapped=False
    try:m.run()
    except TrapBoundary:trapped=True
    try:check(m,c,trapped=trapped)
    except AssertionError as e:raise AssertionError((label,c,str(e)))from e
    seen.update(m.visits);count+=1;traps+=int(trapped)
  coverage[label]=sorted((p-ENTRY)//4 for p in set(range(ENTRY,ENTRY+564,4))-seen);counts[label]=count;total+=count
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  base=0x80300000+low;s=dict(SYMS,D_800D154C=base,D_800D2108=base+0x10000,D_800D1890=base+0x20000,D_800D1891=base+0x20001,D_800D1892=base+0x20002,D_800D1893=base+0x20003,func_150ADA20=0x15300000,func_15075498=0x15310000)
  for path in paths.values():
   for mode,mutation in itertools.product((0,254,255),(0,7)):
    c=replace(Case(),mode=mode,mutation=mutation);m=Oracle(words(path,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 assert all(v==[84,87,88,89,111,112,113]for v in coverage.values())
 report=dict(cases_per_body=counts,total=total,trap_prefix_executions=traps,unreachable_words=coverage,independent_rebases=rebases,original_rng_and_flags=True,scripted_mutations_are_extensions=True,all_selector_rate_and_flag_bytes=True,physical_pointer_alias_guest_only=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
