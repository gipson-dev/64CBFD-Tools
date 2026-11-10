"""Independent nine-selector contract, live helper boundaries and unsigned conversion."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_heading_selector_1507aa48_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_heading_selector_1507aa48_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS;ACTOR=0x20000;ALT_ACTOR=0x21000;TABLE=0x60000;ROWS=(0x70000,0x72000)
CALL_NAMES=('func_150484A0','func_150ADA20')
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
same=lambda a,b:a==b or math.isnan(floating(a))and math.isnan(floating(b))
def trunc(v):
 f=floating(v);n=math.trunc(f)if math.isfinite(f)else-1
 return n if 0<=n<2**32 else 0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 command:int=0
 first:int=1
 second:int=2
 third:int=0x83
 base:int=0xFF80
 heading:int=0x8123
 saved:int=0x1234
 selected:int=1
 group:int=0
 coordinates:tuple=(-32768,32767,32767,-32768)
 angle:int=0x3F000000
 scale:int=0x4622F983
 random:int=0x812345FF
 effects:int=0
 fcsr:int=0
 provider_fcsr:int=0x00800004
 alias:int=0
 phase:int=0

def fixture(c=Case(),s=SYMS,offsets=None,entry=ENTRY):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 array=s['D_800CC34A']-122
 for base,n in((ACTOR,812),(ALT_ACTOR,812),(array,812*26),(TABLE,1024),*((p,2080)for p in ROWS)):
  for i in range(-16,n+16):m.setdefault(base+i,(i*29+0x59)&255)
 for name in('D_800D154C','D_800D1890','D_800D1891','D_800D1892','D_800D1893','D_800D2104','D_8009A20C',qualify.RODATA):
  for i in range(-16,64):m.setdefault(s[name]+i,(i*13+0xA5)&255)
 for base,group in((ACTOR,c.group),(ALT_ACTOR,c.group^1)):
  m[base+546]=c.selected;m[base+319]=group
  for off,v in((118,c.base),(120,c.heading),(122,c.saved)):put(m,base+off,v^(0x55AA if base==ALT_ACTOR else 0),2)
 put(m,s['D_800CC34A']+c.selected*812,0xE137,2)
 for i in range(256):put(m,TABLE+i*4,ROWS[i&1])
 row=ROWS[c.group&1]
 for idx,x,z in((c.first,*c.coordinates[:2]),(c.second,*c.coordinates[2:])):
  put(m,row+(idx+1)*8,x,2);put(m,row+(idx+1)*8+4,z,2)
 put(m,s['D_800D154C'],0 if c.command>=9 else ACTOR);put(m,s['D_800D2104'],TABLE);put(m,s['D_8009A20C'],c.scale)
 for n,v in(('D_800D1890',c.first),('D_800D1891',c.second),('D_800D1892',c.command),('D_800D1893',c.third)):m[s[n]]=v
 if offsets is None:offsets=qualify.DERIVATION['normalized_table_offsets']
 for i,v in enumerate(offsets):put(m,s[qualify.RODATA]+i*4,entry+v)
 if c.alias:
  assert c.command==3
  fake=s['D_800D154C']+2-118;changed=(fake&0xFFFF0000)|0x3000
  for base in(fake,changed):
   for i in range(812):m.setdefault(base+i,0xA5)
  put(m,s['D_800D154C'],fake);put(m,fake+120,0x3000,2);put(m,changed+120,0xBEEF,2)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def snapshot(m):return tuple(sorted(public(m).items()))
def effect(m,c,s=SYMS):
 if c.effects&1:put(m,s['D_800D154C'],ALT_ACTOR)
 if c.effects&2:m[s['D_800D1893']]=0x17
 if c.effects&4:put(m,s['D_8009A20C'],0x40000000)
 if c.effects&8:
  for base in(ACTOR,ALT_ACTOR):put(m,base+120,0x5A81,2);m[base+319]^=1
  put(m,TABLE+c.group*4,ROWS[1-(c.group&1)])
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);calls=[];obs=[];writes=[];value=(m[s['D_800D1890']]<<8)|m[s['D_800D1891']];mode=m[s['D_800D1892']]
 def actor():return read(m,s['D_800D154C'])
 def store(off,value):p=actor()+off;put(m,p,value,2);writes.append((p,value&65535))
 if mode==0:store(120,read(m,actor()+118,2)+value)
 elif mode==1:store(120,read(m,actor()+118,2)-value)
 elif mode==2:store(120,value)
 elif mode==3:store(118,read(m,actor()+120,2));store(122,read(m,actor()+120,2))
 elif mode==4:
  row=read(m,read(m,s['D_800D2104'])+m[actor()+319]*4);p=row+(m[s['D_800D1890']]+1)*8;q=row+(m[s['D_800D1891']]+1)*8
  args=(bits(float(s16(read(m,q,2))-s16(read(m,p,2)))),bits(float(s16(read(m,q+4,2))-s16(read(m,p+4,2)))))
  calls.append((s['func_150484A0'],args));obs.append(snapshot(m));effect(m,c,s)
  product=bits(floating(c.angle)*floating(read(m,s['D_8009A20C'])));store(120,trunc(product)+(m[s['D_800D1893']]<<8)+0x4000)
 elif mode==5:
  calls.append((s['func_150ADA20'],()));obs.append(snapshot(m));effect(m,c,s);store(120,c.random)
 elif mode==6:store(120,read(m,actor()+118,2))
 elif mode==7:store(118,read(m,s['D_800CC34A']+m[actor()+546]*812,2)+value)
 elif mode==8:store(118,read(m,actor()+122,2))
 return m,calls,obs,writes
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.fcsr=c.fcsr
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   f=floating(self.f[w>>11&31]);self.f[w>>6&31]=u32(math.trunc(f))if math.isfinite(f)and-2**31<=f<2**31 else 0x80000000;return
  if w>>26==17 and(w>>21&31 in(2,6)or w>>21&31==16 and w&63==36):return AreaOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  assert t in[self.syms[n]for n in CALL_NAMES],hex(t);args=(self.f[12],self.f[14])if t==self.syms[CALL_NAMES[0]]else();self.calls.append((t,args));self.observations.append(snapshot(self.memory));self.events.append(('CALL',t,args))
 def hook(self,t):
  effect(self.memory,self.case,self.syms)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.angle;self.r[2]=self.case.random;self.hi,self.lo=0xA5000010,0xA5000011;self.fcsr=self.case.provider_fcsr
def words(p,s=SYMS):
 raw,refs=qualify.payload(p);s={**s,'.rodata':s[qualify.RODATA]};return bound_blob(raw,refs,s)
def offsets(p):return qualify.DERIVATION['raw_table_offsets'if len(qualify.payload(p)[0])==612 else'normalized_table_offsets']
def check(m,c=Case(),s=SYMS):
 want,calls,obs,writes=reference(m.initial,c,s);assert m.calls==calls,('ABI',c,m.calls,calls);assert m.observations==obs,('helper snapshots',c)
 assert public(m.memory)==public(want),('public',c,[(hex(p),v,want.get(p))for p,v in public(m.memory).items()if want.get(p)!=v][:6])
 actual=[(p,v)for mode,p,n,v in m.trace if mode=='W'and n==2 and not STACK-1024<=p<STACK+1024];assert actual==writes,('writes',c,actual,writes)
 assert m.fcsr==(c.provider_fcsr if c.command in(4,5)else c.fcsr),('FCSR',c,hex(m.fcsr))
 assert all(m.memory[p]==v for p,v in m.initial.items()if STACK+c.phase<=p<STACK+c.phase+512)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[replace(Case(),command=n,first=n&255,second=(n*71+3)&255,third=(n*23)&255,selected=n%26,group=n&1,phase=(n&1)*8)for n in range(256)]
 for mode in range(9):
  for value in(0,1,0x7FFF,0x8000,0xFFFF):result.append(replace(Case(),command=mode,base=value,heading=value,saved=value,first=value>>8,second=value&255))
 for mode,effects in itertools.product((4,5),range(16)):result.append(replace(Case(),command=mode,effects=effects))
 for v in(0,0x80000000,0x3F000000,0xBF000000,0xBF800000,0x3FFFFFFF,0x4EFFFFFF,0x4F000000,0x4F000001,0x4F7FFFFF,0x4F800000,0xCF000000,0x7F800000,0xFF800000,0x7FC12345):result.append(replace(Case(),command=4,angle=v,scale=0x3F800000))
 for csr in(0,0x00800004,0x00800005,0x00800006,0x00800007):result.append(replace(Case(),command=4,angle=0x4F000001,scale=0x3F800000,provider_fcsr=csr))
 result.append(replace(Case(),command=3,alias=1));return result
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_A28B0.c.o','retail':out/'retail-linked.o'};coverage={};cs=cases()
 for label,p in paths.items():
  seen=set()
  for c in cs:m=Oracle(words(p),fixture(c,offsets=offsets(p)),c);m.run();check(m,c);seen.update(m.visits)
  coverage[label]=len(seen&set(range(ENTRY,ENTRY+len(words(p))*4,4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(SYMS)}
  for mode in range(9):
   c=replace(Case(),command=mode,effects=15,phase=(mode&1)*8);entry=ENTRY+0x4000;m=Oracle(words(paths['raw'],s),fixture(c,s,offsets(paths['raw']),entry),c,entry=entry,s=s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=len(cs),executions=3*len(cs),coverage=coverage,independent_rebases=rebases,all_public_bytes=True,ordered_u16_stores=True,all_256_selectors=True,live_actor_scale_and_third_byte=True,physical_global_alias=True,unsigned_conversion_guest_boundaries=True,bounded_FCSR_conversion_save_restore=True,full_hardware_FCSR=False,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
