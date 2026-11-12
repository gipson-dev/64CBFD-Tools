import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_resource_reference_release_15132444_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x15132444;OWNER=0x30000;NODE=0x50000;PREV=0x60000;NEXT=0x70000;RESOURCE=0x80000;AUX=0x90000;NODE2=0xA0000;MARK=0xB0000
HEAD=0x800DC460;TAIL=0x800DC464;REFS=0x800DC468;COUNT=0x800DC63C;TABLE=0x800DC640
RELEASE_AUX=0x1510D630;FREE=0x100043B4;CLEANUP=0x151325C8
ranges=((STACK-1024,STACK+512),(OWNER,OWNER+0x180),(NODE,NODE+0x20),(PREV,PREV+0x20),(NEXT,NEXT+0x20),(RESOURCE,RESOURCE+0x20),(AUX,AUX+0x20),(NODE2,NODE2+0x20),(MARK,MARK+0x20),(HEAD,HEAD+0x600))
assert all(b<=c or d<=a for i,(a,b) in enumerate(ranges)for c,d in ranges[i+1:]),'Guest fixture regions overlap'
@dataclass(frozen=True)
class Case:
 index:int;refs:int;retained:int;previous:int;following:int;mutate:int;phase:int=0
def cases():return [Case(*v)for v in itertools.product((0,1,233),(-4,0,1,2),(0,1),(0,1),(0,1),(0,1))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((OWNER,0x180),(NODE,0x20),(PREV,0x20),(NEXT,0x20),(RESOURCE,0x20),(AUX,0x20),(NODE2,0x20),(MARK,0x20),(HEAD,0x600)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,OWNER+0x66,c.index,2);put(m,OWNER+0x8c,NODE);put(m,NODE,RESOURCE);put(m,NODE+4,NEXT if c.following else 0);put(m,NODE+8,PREV if c.previous else 0);m[NODE+0xe]=c.retained
 put(m,PREV+4,NODE);put(m,NEXT+8,NODE);put(m,NODE2,RESOURCE);put(m,HEAD,PREV if c.previous else NODE);put(m,TAIL,NEXT if c.following else NODE);put(m,COUNT,10);put(m,REFS+2*c.index,c.refs,2);put(m,TABLE+4*c.index,AUX);put(m,MARK,0)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def reference(c):
 m=fixture(c);calls=[];put(m,COUNT,read(m,COUNT)-1);put(m,REFS+2*c.index,c.refs-1,2)
 if c.refs-1==0:
  if c.retained:put(m,REFS+2*c.index,1,2)
  else:
   calls.append((RELEASE_AUX,(AUX,)))
   if c.mutate:put(m,NODE+4,0 if c.following else NEXT)
   node=read(m,OWNER+0x8c);following=read(m,node+4);previous=read(m,node+8)
   if not previous:
    put(m,HEAD,following)
    if following:put(m,following+8,0)
    else:put(m,TAIL,0)
   else:
    put(m,previous+4,following);node=read(m,OWNER+0x8c);following=read(m,node+4);previous=read(m,node+8)
    if following:put(m,following+8,previous)
    else:put(m,TAIL,previous)
   calls.append((FREE,(read(m,read(m,OWNER+0x8c)),4)))
   if c.mutate:put(m,OWNER+0x8c,NODE2)
   calls.append((FREE,(read(m,OWNER+0x8c),4)))
 calls.append((CLEANUP,(OWNER,)));put(m,OWNER+0x154,0x13579bdf);return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,));self.before=self.r[:];self.before_f=self.f[:];self.frees=0
 def record_call(self,t):
  assert t in (RELEASE_AUX,FREE,CLEANUP),hex(t);args=tuple(self.arguments(2 if t==FREE else 1));self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  if t==RELEASE_AUX and c.mutate:put(self.memory,NODE+4,0 if c.following else NEXT)
  elif t==FREE:
   self.frees+=1
   if self.frees==1 and c.mutate:put(self.memory,OWNER+0x8c,NODE2)
  elif t==CLEANUP:put(self.memory,OWNER+0x154,0x13579bdf)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_15132444']['value'],fs['func_15132444']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x15F8F4);seen=set();count=0
 for c in cases():
  expected,calls=reference(c);models=[Oracle(ws,c)for ws in(retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.calls==calls,(c,label,'calls',m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(75)),helpers='modeled',return_register_unqualified=True,valid_disjoint_resource_storage=True,source_installed=False);(out/'guest_15132444_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
