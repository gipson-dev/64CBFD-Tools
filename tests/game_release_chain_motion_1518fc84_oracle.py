import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_release_chain_motion_1518fc84_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1518FC84;OWNER=0x30000;CHILD=0x50000;PARAM=0x60000;TARGET=0x70000;MARK=0x80000
RELEASE=0x1516972C;RANDOM_FLOAT=0x150ADA68;RANDOM_INT=0x150ADA20
ranges=((STACK-1024,STACK+512),(OWNER,OWNER+0x80),(CHILD,CHILD+0x180),(PARAM,PARAM+0x100),(TARGET,TARGET+0x20),(MARK,MARK+0x20))
assert all(b<=c or d<=a for i,(a,b)in enumerate(ranges)for c,d in ranges[i+1:]),'Guest fixture regions overlap'
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
real=lambda x:struct.unpack('>f',struct.pack('>I',x&0xffffffff))[0]
f32=lambda x:real(bits(x))
@dataclass(frozen=True)
class Case:
 present:int;alias:int;mutate:int;flag:int;span:int;rng:int;scale:float;null_target:int=0;phase:int=0
def cases():
 cs=[Case(*v)for v in itertools.product((0,1),(0,1),(0,1),(0,1),(0,1,7,30),(0,1,0x80000000,0xffffffff),(-2.,0.,.5))]
 return cs+[Case(0,0,mut,0,span,rng,1.,1)for mut,span,rng in itertools.product((0,1),(0,7),(0,0xffffffff))]
def target_for(c):return 0 if c.null_target else OWNER+0x34 if c.alias else TARGET
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((OWNER,0x80),(CHILD,0x180),(PARAM,0x100),(TARGET,0x20),(MARK,0x20)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,OWNER+0x2c,CHILD);put(m,OWNER+0x30,PARAM if c.present else 0)
 for i,x in enumerate((1.,-2.,3.)):put(m,OWNER+0x34+4*i,bits(x))
 for i,x in enumerate((4.,1.,-1.)):put(m,TARGET+4*i,bits(x))
 for off,x in ((0x60,c.scale),(0x64,2.),(0x68,-.5),(0x6c,5.)):put(m,PARAM+off,bits(x))
 for off,x in ((0x70,-11),(0x72,22),(0x74,-100),(0x76,c.span)):put(m,PARAM+off,x,2)
 m[PARAM+0x7c]=c.flag;put(m,CHILD+0x58,0x01020304);put(m,MARK,0)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def float_mutate(m):
 for off,x in ((0x64,10.),(0x68,-2.),(0x6c,17.)):put(m,PARAM+off,bits(x))
 put(m,PARAM+0x70,-7,2);put(m,PARAM+0x72,12,2)
def int_mutate(m):put(m,PARAM+0x74,13,2);put(m,PARAM+0x76,3,2);m[PARAM+0x7c]^=1
def signed16(v):return ((v&0xffff)^0x8000)-0x8000
def reference(c):
 m=fixture(c);calls=[]
 if not c.present:
  calls.append((RELEASE,(CHILD,)));put(m,MARK,0x13579bdf);return public(m),calls
 target=target_for(c)
 for i in range(3):
  delta=f32(real(read(m,target+4*i))-real(read(m,OWNER+0x34+4*i)));put(m,CHILD+0x148+4*i,bits(f32(delta*real(read(m,PARAM+0x60)))))
 calls.append((RANDOM_FLOAT,()))
 if c.mutate:float_mutate(m)
 value=f32(f32(.5*real(read(m,PARAM+0x68)))+real(read(m,PARAM+0x64)));put(m,CHILD+0x154,bits(value));put(m,CHILD+0x158,read(m,PARAM+0x6c));put(m,CHILD+0x6c,read(m,PARAM+0x70,2),2);put(m,CHILD+0x6e,read(m,PARAM+0x72,2),2)
 calls.append((RANDOM_INT,()))
 if c.mutate:int_mutate(m)
 base=signed16(read(m,PARAM+0x74,2));span=signed16(read(m,PARAM+0x76,2));put(m,CHILD+0x1c,(c.rng%(span+1))+base,2);m[CHILD+0x70]=0x21 if m[PARAM+0x7c]&1 else 0x20;m[CHILD+0x71]=0x24;put(m,CHILD+0x58,read(m,CHILD+0x58)|0x08000001)
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,target_for(c)));self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==0x1b:
   rs,rt=w>>21&31,w>>16&31;num,den=self.r[rs]&0xffffffff,self.r[rt]&0xffffffff;assert den;self.lo,self.hi=divmod(num,den);self.r[0]=0;return
  super().execute(w)
 def record_call(self,t):assert t in(RELEASE,RANDOM_FLOAT,RANDOM_INT),hex(t);self.calls.append((t,tuple(self.arguments(1))if t==RELEASE else ()))
 def hook(self,t):
  if t==RELEASE:put(self.memory,MARK,0x13579bdf)
  elif t==RANDOM_FLOAT and self.case.mutate:float_mutate(self.memory)
  elif t==RANDOM_INT and self.case.mutate:int_mutate(self.memory)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.case.rng if t==RANDOM_INT else 0xDEADBEEF
  if t==RANDOM_FLOAT:self.f[0]=bits(.5)
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_1518FC84']['value'],fs['func_1518FC84']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>80I',(root/'conker/conker.us.bin').read_bytes(),0x1BD134);seen=set();count=0
 for c in cases():
  expected,calls=reference(c);models=[Oracle(ws,c)for ws in(retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.calls==calls,(c,label,'calls',m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(80)),helpers='modeled',valid_finite_inputs_and_owner_target_alias=True,zero_divisor_excluded=True,return_register_unqualified=True,source_installed=False);(out/'guest_1518FC84_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
