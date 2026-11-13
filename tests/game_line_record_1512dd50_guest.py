"""Private finite-value screen using the connected retail length helper."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable';rom=(root/'conker/conker.us.bin').read_bytes()
ENTRY=0x1512dd50;HELPER=0x150ad930;OWNER=0x320000
helper=list(struct.unpack_from('>11I',rom,0xdade0));connected={HELPER+i*4:w for i,w in enumerate(helper)}
@dataclass(frozen=True)
class Case:
 position:tuple;size:int;axes:tuple;first:int;second:int;kind:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)};m.update({OWNER+i:(i*29+0x35)&255 for i in range(-16,0xa00)})
 for i,v in enumerate((*c.position,c.size)):put(m,OWNER+0x70c+2*i,v&65535,2)
 for i,v in enumerate(c.axes):put(m,OWNER+0x720+i*4,bits(v))
 for off,value in ((0x71c,c.first),(0x704,c.second),(0x718,c.kind)):put(m,OWNER+off,value)
 return m
def f32(v):return floating(bits(v))
def u32float(v):
 value=f32(float(signed(v)))
 return f32(value+4294967296.0) if v&0x80000000 else value
def reference(initial,c):
 m=dict(initial);size=f32(float(c.size));scale=f32(c.axes[0]*size);dy=f32(c.axes[1]*size);dx=f32(c.axes[2]*scale);dz=f32(-scale*c.axes[3])
 for off,value in ((0x874,f32(float(c.position[0])-dx)),(0x878,f32(float(c.position[1])-dy)),(0x87c,f32(float(c.position[2])-dz))):put(m,OWNER+off,bits(value))
 vector=[f32(dx+dx),f32(dy+dy),f32(dz+dz)];summed=f32(f32(f32(vector[0]*vector[0])+f32(vector[1]*vector[1]))+f32(vector[2]*vector[2]));length=f32(math.sqrt(summed));assert length!=0
 inv=f32(1.0/length);put(m,OWNER+0x88c,bits(inv))
 for i,value in enumerate(vector):put(m,OWNER+0x880+i*4,bits(f32(inv*value)))
 put(m,OWNER+0x890,bits(u32float(c.first)));put(m,OWNER+0x894,bits(u32float(c.second)));put(m,OWNER+0x898,0);put(m,OWNER+0x89c,0);m[OWNER+0x870]=c.kind&255
 return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512},tuple(bits(v) for v in vector)
class Machine(FactoryOracle):
 def __init__(self,w,m,c):super().__init__(w,m,c,entry=ENTRY,s={},connected=connected,arguments=(OWNER,))
 def execute(self,word):
  op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
  if op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000;return
  if op==17 and rs==16 and fn==4:self.f[fd]=bits(math.sqrt(floating(self.f[rd])));return
  return super().execute(word)
 def record_call(self,t):
  assert t==HELPER;pointer=self.r[4];self.calls.append((t,tuple(read(self.memory,pointer+4*i) for i in range(3))))
 def hook(self,t):raise AssertionError(('unexpected external helper',hex(t)))
def main():
 original=list(struct.unpack_from('>85I',rom,0x15b200));programs=[original]
 for name in ('pointer-reuse-00.o','explicit-padded.o'):
  raw,refs=payload(out/name,'func_1512DD50');programs.append(bound_blob(raw,refs,{'func_150AD930':HELPER}))
 count=0
 for pos,size,axes,first,second,phase in itertools.product(((1,-2,3),(-32768,32767,-1)),(-2,3,32767),((0.5,1.0,2.0,-0.25),(-1.25,0.75,-0.5,2.0)),(0,0x7fffffff,0x80000001,0x80000081,0xffffffff),(0,0xffffffff),(0,8)):
  c=Case(pos,size,axes,first,second,0x123456e1,phase);initial=fixture(c);expected,vector=reference(initial,c)
  for p in programs:
   m=Machine(p,initial.copy(),c).run();actual={a:v for a,v in m.memory.items() if not STACK-512<=a<STACK+512}
   assert actual==expected and m.calls==[(HELPER,vector)],(c,m.calls,[(hex(a),actual.get(a),expected.get(a)) for a in expected if actual.get(a)!=expected.get(a)][:12])
  count+=1
 report={'cases':count,'streams':len(programs),'connected_retail_helper_words':11,'finite_nonzero_length_only':True,'independent_f32_model':True,'uncredited':True};(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
