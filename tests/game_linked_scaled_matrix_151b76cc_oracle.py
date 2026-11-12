import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_linked_scaled_matrix_151b76cc_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151B76CC;OWNER=0x30000;DATA=0x50000;LINK=0x60000;SOURCE=0x70000;OUTPUT=0x80000
ROTATE=0x150A8050;TRANSFORM=0x150A7960
ranges=((STACK-1024,STACK+512),(OWNER,OWNER+0xA0),(DATA,DATA+0x20),(LINK,LINK+0x20),(SOURCE,SOURCE+0x80),(OUTPUT,OUTPUT+0x20))
assert all(b<=c or d<=a for i,(a,b) in enumerate(ranges) for c,d in ranges[i+1:]),'Guest fixture regions overlap'
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
real=lambda x:struct.unpack('>f',struct.pack('>I',x&0xffffffff))[0]
f32=lambda x:real(bits(x))
@dataclass(frozen=True)
class Case:
 sx:float;sy:float;translation:float;seed:int;mutate:int;alias:int;phase:int=0
def cases():
 return [Case(sx,sy,pos,seed,mutate,alias) for sx,sy,pos,seed,mutate,alias in itertools.product((-2.,-0.,.5,1.,2.),(-2.,-0.,.5,1.,2.),(-3.,0.,9.),range(2),(0,1),(0,1))]
def output_for(c):return OWNER+0x10 if c.alias else OUTPUT
def matrix_words(c):return tuple(bits((i-7+c.seed)*.25) for i in range(16))
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((OWNER,0xA0),(DATA,0x20),(LINK,0x20),(SOURCE,0x80),(OUTPUT,0x20)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,OWNER+0x98,DATA);put(m,DATA+4,LINK);put(m,LINK,SOURCE)
 for off,val in ((0x18,c.sx),(0x1c,c.sy),(0x20,10.+c.seed),(0x24,-20.-c.seed),(0x28,30.+c.seed),(0x38,c.translation),(0x3c,c.translation+1.),(0x40,c.translation+2.)):put(m,SOURCE+off,bits(val))
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m):
 for off,val in ((0x18,-.75),(0x1c,1.25),(0x38,7.),(0x3c,8.),(0x40,9.)):put(m,SOURCE+off,bits(val))
def expected_matrix(m,c):
 words=list(matrix_words(c));words[12:15]=[read(m,SOURCE+off)for off in (0x38,0x3c,0x40)]
 for row,scale in ((0,real(read(m,SOURCE+0x18))),(1,real(read(m,SOURCE+0x1c))),(2,real(read(m,SOURCE+0x18)))):
  for col in range(3):i=4*row+col;words[i]=bits(f32(real(words[i])*scale))
 return tuple(words)
def output_words(matrix):return tuple(matrix[i]^0x00000001 for i in (0,5,10))
def reference(c):
 m=fixture(c);rot=tuple(read(m,SOURCE+off)for off in (0x20,0x24,0x28));calls=[(ROTATE,rot)]
 if c.mutate:mutate(m)
 matrix=expected_matrix(m,c);target=output_for(c);calls.append((TRANSFORM,(matrix,0,0,bits(-250.),(target,target+4,target+8))))
 for i,v in enumerate(output_words(matrix)):put(m,target+4*i,v)
 return public(m),calls,1
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,output_for(c)));self.before=self.r[:];self.before_f=self.f[:];self.helper_args=None
 def record_call(self,t):
  assert t in (ROTATE,TRANSFORM),hex(t);raw=tuple(self.arguments(4 if t==ROTATE else 7));self.helper_args=raw
  if t==ROTATE:args=raw[1:]
  else:args=(tuple(read(self.memory,raw[0]+4*i)for i in range(16)),*raw[1:4],tuple(raw[4:7]))
  self.calls.append((t,args))
 def hook(self,t):
  c=self.case;raw=self.helper_args
  if t==ROTATE:
   for i,v in enumerate(matrix_words(c)):put(self.memory,raw[0]+4*i,v)
   if c.mutate:mutate(self.memory)
  else:
   matrix=tuple(read(self.memory,raw[0]+4*i)for i in range(16))
   for p,v in zip(raw[4:7],output_words(matrix)):put(self.memory,p,v)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_151B76CC']['value'],fs['func_151B76CC']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0x1E4B7C);seen=set();count=0
 for c in cases():
  expected,calls,answer=reference(c);models=[Oracle(ws,c)for ws in(retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.calls==calls,(c,label,'calls',m.calls,calls);assert m.r[2]==answer,(c,label,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),helpers='modeled',valid_finite_storage_with_owner_output_alias=True,source_installed=False);(out/'guest_151B76CC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
