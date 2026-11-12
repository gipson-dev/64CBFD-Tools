import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_paired_packet_constructors_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
OWNER=0x30000;ALLOC=0x15189ff0;ATTACH=0x1514ec1c;EFFECT=0x151d74b0
@dataclass(frozen=True)
class Case:
 identity:int; answer:int; seed:int; phase:int; mutate:int; first:int; second:int
def cases():
 for identity,answer,seed,phase,mutate in itertools.product((0,1,127,128,255),(0,0x50000),(0,17),(0,8),(0,1)):
  yield Case(identity,answer,seed,phase,mutate,0x3f123456^(seed<<8),0xc0056789^(identity<<8))
def fixture(c,global_address):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 m.update({OWNER+i:(i*11+c.seed)&255 for i in range(256)})
 m[OWNER+0x3b]=c.identity;put(m,global_address,c.first);put(m,global_address+4,c.second)
 return m
def expected(c,width,global_address):
 m=fixture(c,global_address);sp=STACK+c.phase-0x100;d,s,r=sp+0x4c,sp+0xa4,sp+0x2c
 for offset,value,size in ((0,3,1),(2,0x401,2),(4,0,2),(8,0,4),(12,0,4),(0x10,255,1),(0x11,0x8e,1),(0x12,0x19,1),(0x13,255,1),(0x40,0x12002,4),(0x45,255,1)):
  put(m,d+offset,value,size)
 for offset in range(0x1c,0x34,4):put(m,d+offset,0)
 for offset in range(0,0x10,4):put(m,s+offset,width)
 for offset,value in ((0x10,0),(0x14,0),(0x18,0x3f000000),(0x1c,0x3f000000),(0x20,c.first),(0x48,0x3f800000),(0x54,0)):put(m,s+offset,value)
 for offset,value in enumerate((0x420c0000,0x41d80000,0x426c0000,0x420c0000,0x41d80000,c.second)):put(m,r+offset*4,value)
 put(m,r+0x18,OWNER);put(m,r+0x1c,6,1);put(m,r+0x1d,c.identity,1);put(m,r+0x1e,255,1)
 packet=lambda p,n:bytes(m[p+i] for i in range(n))
 return (packet(d,0x58),packet(s,0x5c),packet(r,0x20))
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry,global_address):
  super().__init__(words,fixture(c,global_address),c,entry=entry,arguments=(OWNER,));self.before=self.r[:];self.before_f=self.f[:];self.packet=None
 def record_call(self,t):
  count={ALLOC:7,ATTACH:3,EFFECT:5}[t];args=tuple(self.arguments(count));self.calls.append((t,args))
  if t==ALLOC:
   self.packet=tuple(bytes(self.memory[p+i] for i in range(n)) for p,n in zip(args[:3],(0x58,0x5c,0x20)))
 def hook(self,t):
  if t==ALLOC and self.case.mutate:self.memory[OWNER+0x3b]^=0x55
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  self.r[2]=self.case.answer if t==ALLOC else 0x12345678 if t==ATTACH else 0x87654321
def main():
 raw,fs,rs=parse_object(out/'paired.o');look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};rom=(root/'conker/conker.us.bin').read_bytes();reports=[]
 for name,entry,offset,width,glob in (('func_1514E00C',0x1514e00c,0x17b4bc,0x41a00000,0x800a5e08),('func_1514E194',0x1514e194,0x17b644,0x41800000,0x800a5e10)):
  a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};candidate=bound_blob(raw[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>98I',rom,offset);seen=set();count=0
  for c in cases():
   expected_packet=expected(c,width,glob);sp=STACK+c.phase-0x100
   for ws in (retail,candidate):
    m=Oracle(ws,c,entry,glob);m.run()
    assert m.packet==expected_packet,(name,c,'packet')
    assert m.calls==[(ALLOC,(sp+0x4c,sp+0xa4,sp+0x2c,2,0,0,0)),(ATTACH,(c.answer,OWNER,6)),(EFFECT,(OWNER,5,0xffffffff,255,1))],(name,c,m.calls)
    assert m.r[2]==0x87654321 and m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
    if ws is retail:seen.update(m.visits)
   count+=1
  reports.append(dict(target=name,cases=count,retail_words_visited=sum(entry+4*i in seen for i in range(98)),helpers='modeled'))
 result=dict(targets=reports,source_installed=False);(out/'guest_screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
