import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_animated_packet_renderer_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x15167c58;SETUP=0x15142e24;MODE=0x15142fbc;DRAW=0x15095760;STATE=0x30000;OUTPUT=0x40000;TEXTURE=0x50000;FRAMES=0x60000;FLAGS=0x800a4ac8
@dataclass(frozen=True)
class Case:
 seed:int;animation:int;mode:int;mutate:int;phase:int
def cases():return [Case(*x)for x in itertools.product(range(3),(-257,-1,0,0x100,0x2ff),(0,0x7f,0x80,0xff),range(2),(0,8))]
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 for base,n in ((STATE,0x30),(TEXTURE,16),(FRAMES-16,64),(FLAGS,96)):
  m.update({base+i:(i*29+c.seed*7+5)&255 for i in range(n)})
 put(m,STATE+0x10,TEXTURE);put(m,TEXTURE,FRAMES);put(m,STATE+0x14,c.animation&0xffff,2)
 for i in range(-4,8):put(m,FRAMES+4*i,0x12340000+i+c.seed)
 for i in range(5):put(m,STATE+0x18+2*i,(i*0x1111+c.seed*0x111)&0xffff,2)
 m[STATE+0x22]=c.mode;m[STATE+0x23]=(c.seed*71+5)&255
 return m
def effect(m,c,t,packet,sync):
 if not c.mutate:return
 if t==SETUP:
  for i in range(5):put(m,STATE+0x18+2*i,(0x8001+i*79+c.seed)&0xffff,2)
  m[STATE+0x22]^=0xff;m[STATE+0x23]^=0x55;m[packet+0xb]^=0x5a;m[sync]^=0x5a
  put(m,FLAGS+24,0x12345678);put(m,FLAGS+28,0x87654321)
 if t==MODE:m[packet+2]^=0x33;m[sync]^=0xa5
def reference(c):
 m=fixture(c);sp=STACK+c.phase-0x70;sync=sp+0x50;packet=sp+0x5c;put(m,sync,1);calls=[];packets=[]
 frame=read(m,FRAMES+4*(c.animation>>8));calls.append((SETUP,(OUTPUT,TEXTURE,(c.animation<<8)&0xffffffff,2,256,256,frame,5,packet,sync,3)));packets.append(bytes(m[packet+i]for i in range(20)));effect(m,c,SETUP,packet,sync)
 for i in range(5):put(m,packet+2*i,read(m,STATE+0x18+2*i,2),2)
 m[packet+0xa]=m[STATE+0x23];m[packet+0xd]=0
 # The sign-extended byte can never equal positive 255: the retail branch uses mode 3.
 flags=read(m,FLAGS+24)|read(m,FLAGS+28)|4;calls.append((MODE,(OUTPUT+0x20,0x2c00,flags,sync)));effect(m,c,MODE,packet,sync)
 calls.append((DRAW,(OUTPUT+0x40,packet)));packets.append(bytes(m[packet+i]for i in range(20)))
 return calls,packets,{a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(OUTPUT,STATE,0xabcdef01));self.before=self.r[:];self.before_f=self.f[:];self.packets=[]
 def record_call(self,t):
  assert t in (SETUP,MODE,DRAW),hex(t);args=tuple(self.arguments({SETUP:11,MODE:4,DRAW:2}[t]));self.calls.append((t,args))
  if t in (SETUP,DRAW):
   p=args[8]if t==SETUP else args[1];self.packets.append(bytes(self.memory[p+i]for i in range(20)))
 def hook(self,t):
  sp=STACK+self.case.phase-0x70;effect(self.memory,self.case,t,sp+0x5c,sp+0x50)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]={SETUP:OUTPUT+0x20,MODE:OUTPUT+0x40,DRAW:OUTPUT+0x60}[t]
def main():
 data,fs,rs=parse_object(out/'candidate.o');a,n=fs['func_15167C58']['value'],fs['func_15167C58']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x195108);seen=set()
 for c in cases():
  calls,packets,public=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();actual={a:v for a,v in m.memory.items()if not STACK-1024<=a<STACK+512}
   assert (m.calls,m.packets,actual,m.r[2])==(calls,packets,public,OUTPUT+0x60),(c,m.calls,calls,m.packets,packets)
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
 missed=[hex(ENTRY+4*i)for i in range(75)if ENTRY+4*i not in seen]
 report=dict(cases=len(cases()),retail_words_visited=75-len(missed),unvisited_words=missed,helpers='modeled',source_installed=False);(out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
