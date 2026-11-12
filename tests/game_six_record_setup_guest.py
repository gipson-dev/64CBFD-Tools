import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_six_record_setup_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x15010110;SETUP=0x15195aa8;EMIT=0x151acbd4;OBJECTS=0x800b0e00;PARAM=0x800902e8;RECORDS=0x800963a0
@dataclass(frozen=True)
class Case:
 seed:int;pattern:int;mutate:int;phase:int
def cases():return [Case(*x)for x in itertools.product(range(3),range(6),range(2),(0,8))]
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 for base,n in ((OBJECTS,8),(PARAM,4),(RECORDS,6*24)):
  m.update({base+i:(i*29+c.seed*7+5)&255 for i in range(n)})
 put(m,OBJECTS,0x12340000+c.seed);put(m,OBJECTS+4,0x56780000+c.seed);put(m,PARAM,0x13570000+c.pattern)
 vals=((-100.,100.),(0.,0.),(-0.,0.),(1.25,-3.5),(32768.,-16384.),(-1.e10,1.e-5))
 for i in range(6):
  x,y=vals[(c.pattern+i)%6];put(m,RECORDS+i*24+4,bits(x));put(m,RECORDS+i*24+16,bits(y))
 return m
def effect(m,c,t,index,record):
 if not c.mutate:return
 if t==SETUP and index==1:
  put(m,OBJECTS+4,0x87654321);put(m,PARAM,0xabcdef12)
 if t==EMIT:
  m[record+0x20]^=0x5a
  if index<6:put(m,RECORDS+index*24+4,bits(-17.25-index))
def reference(c):
 m=fixture(c);frame=STACK+c.phase-0x70;record=frame+0x4c;calls=[];packets=[]
 for i in range(2):
  calls.append((SETUP,(read(m,OBJECTS+i*4),read(m,PARAM),0,0xffffffff,0,i,0,0xfffffff8)));effect(m,c,SETUP,i+1,record)
 m[record+0x20]=0
 for i in range(6):
  for j in range(24):m[record+4+j]=m[RECORDS+i*24+j]
  m[record]=i+1;put(m,record+0x1c,fp(read(m,record+8),read(m,record+0x14),'sub')&0x7fffffff)
  calls.append((EMIT,(record,0)));packets.append(bytes(m[record+j]for j in range(0x21)));effect(m,c,EMIT,i+1,record)
 return calls,packets,{a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(0x87654321,));self.before=self.r[:];self.before_f=self.f[:];self.packets=[];self.indices={SETUP:0,EMIT:0}
 def execute(self,word):
  if word>>26==17 and (word>>21)&31==16 and word&63==5:self.f[(word>>6)&31]=self.f[(word>>11)&31]&0x7fffffff
  else:super().execute(word)
 def record_call(self,t):
  assert t in (SETUP,EMIT),hex(t);self.indices[t]+=1;a=tuple(self.arguments(8 if t==SETUP else 2));self.calls.append((t,a))
  if t==EMIT:self.packets.append(bytes(self.memory[a[0]+j]for j in range(0x21)))
 def hook(self,t):
  effect(self.memory,self.case,t,self.indices[t],STACK+self.case.phase-0x70+0x4c)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]=0x60000000+self.indices[t]
def main():
 data,fs,rs=parse_object(out/'candidate.o');a,n=fs['func_15010110']['value'],fs['func_15010110']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0x3d5c0);seen=set()
 for c in cases():
  calls,packets,public=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();actual={a:v for a,v in m.memory.items()if not STACK-1024<=a<STACK+512}
   assert (m.calls,m.packets,actual)==(calls,packets,public),(c,m.calls,calls,m.packets[:1],packets[:1])
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),helpers='modeled',source_installed=False);(out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
