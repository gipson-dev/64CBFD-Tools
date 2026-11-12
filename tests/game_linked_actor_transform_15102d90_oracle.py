import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_linked_actor_transform_15102d90_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x15102D90;OWNER=0x30000;ACTOR=0x80000;MATRIX=0x90000;DESC=0xA0000
FIND=0x1503195C;DESCRIPTOR_TRANSFORM=0x1514654C;MATRIX_TRANSFORM=0x15145EA4
ranges=((STACK-256,STACK+512),(OWNER,OWNER+0x180),(ACTOR,ACTOR+0x220),(MATRIX,MATRIX+0x100),(DESC,DESC+0x100))
assert all(b<=c or d<=a for i,(a,b) in enumerate(ranges) for c,d in ranges[i+1:]),'Guest fixture regions overlap'
u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
 identity:int;actor_identity:int;active:int;matrix:int;mode:int;descriptor:int;found:int;ok:int;mutate:int;flags:int=0xA4;phase:int=0
def cases():
 return [Case(ident,actor,active,matrix,mode,desc,found,ok,mutate,flags) for ident,actor,active,matrix,mode,desc,found,ok,mutate,flags in itertools.product((1,2),(1,2),(0,1),(0,1),(0,15),(-1,0,32767,-32768),(0,1),(0,1),(0,1),(0xA4,0xA7))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-256,512)}
 for base,n in ((OWNER,0x180),(ACTOR,0x220),(MATRIX,0x100),(DESC,0x100)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,OWNER+0x110,ACTOR);m[OWNER+0x114]=c.identity;put(m,OWNER+0x118,0x20);put(m,OWNER+0x11c,c.descriptor,2);put(m,OWNER+0x120,0x12345678);m[OWNER+0x124]=c.flags;put(m,ACTOR,c.active);m[ACTOR+0x3b]=c.actor_identity;m[ACTOR+0x74]=c.mode;put(m,ACTOR+0x1d4,MATRIX if c.matrix else 0)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+512}
def transform(m):
 for i in range(2):
  for j in range(12):m[OWNER+0x128+12*i+j]=m[OWNER+0x34+12*i+j]^0x5a
def reference(c):
 m=fixture(c);calls=[];m[OWNER+0x124]&=0xfe
 if c.identity!=c.actor_identity or not c.active:return public(m),calls,0
 if not c.matrix or (c.mode&15)==15:return public(m),calls,1
 inputs=(OWNER+0x34,OWNER+0x40);outputs=(OWNER+0x128,OWNER+0x134)
 if c.descriptor!=-1:
  calls.append((FIND,(ACTOR,u32(c.descriptor),0)))
  if c.mutate:m[OWNER+0x124]^=0x40;put(m,OWNER+0x120,0x87654321)
  if not c.found:return public(m),calls,0
  calls.append((DESCRIPTOR_TRANSFORM,(ACTOR,DESC,read(m,OWNER+0x120),inputs,outputs,2)))
  if c.mutate:m[OWNER+0x124]^=0x20
  if not c.ok:return public(m),calls,0
  transform(m)
 else:
  calls.append((MATRIX_TRANSFORM,(inputs,outputs,MATRIX+0x20,2)))
  if c.mutate:m[OWNER+0x124]^=0x20
  transform(m)
 m[OWNER+0x124]|=1
 return public(m),calls,1
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in (FIND,DESCRIPTOR_TRANSFORM,MATRIX_TRANSFORM),hex(t);raw=tuple(self.arguments(3 if t==FIND else 6 if t==DESCRIPTOR_TRANSFORM else 4))
  if t==DESCRIPTOR_TRANSFORM:args=(*raw[:3],tuple(read(self.memory,raw[3]+4*i)for i in range(2)),tuple(read(self.memory,raw[4]+4*i)for i in range(2)),raw[5])
  elif t==MATRIX_TRANSFORM:args=(tuple(read(self.memory,raw[0]+4*i)for i in range(2)),tuple(read(self.memory,raw[1]+4*i)for i in range(2)),raw[2],raw[3])
  else:args=raw
  self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  if t==FIND:
   if c.mutate:self.memory[OWNER+0x124]^=0x40;put(self.memory,OWNER+0x120,0x87654321)
   value=DESC if c.found else 0
  else:
   if c.mutate:self.memory[OWNER+0x124]^=0x20
   if t==MATRIX_TRANSFORM or c.ok:transform(self.memory)
   value=c.ok if t==DESCRIPTOR_TRANSFORM else 0xDEADBEEF
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_15102D90']['value'],fs['func_15102D90']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0x130240);seen=set();count=0
 for c in cases():
  expected,calls,answer=reference(c);models=[Oracle(ws,c)for ws in(retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.calls==calls,(c,label,'calls',m.calls,calls);assert m.r[2]==answer,(c,label,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),helpers='modeled',valid_disjoint_owner_actor_and_matrix=True,source_installed=False);(out/'guest_15102D90_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
