import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_tile_fade_callback_150dfdd0_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150DFDD0;OWNER=0x30000;MODEL=0x50000;FADE=0x60000;COMMAND=0x70000;TICK=0x800BE9A4
regions=((STACK-1024,STACK+512),(OWNER,OWNER+0x80),(MODEL,MODEL+0x20),(FADE,FADE+0x300),(COMMAND,COMMAND+0x100),(TICK,TICK+4))
assert all(b<=c or d<=a for i,(a,b) in enumerate(regions) for c,d in regions[i+1:])
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
real=lambda x:struct.unpack('>f',struct.pack('>I',x&0xffffffff))[0]
f32=lambda x:real(bits(x))
@dataclass(frozen=True)
class Case:
 active:int;remaining:float;tick:float;scale:float;has_list:int;index:int;field:int;null_model:int=0;phase:int=0;seed:int=0
def cases():
 return [Case(*v) for v in itertools.product((0,1),(-1.,0.,.5,2.),(0.,.5,1.),(-.5,0.,.5),(0,1),(0,1,5),(0,3,6,9,4095))]+[Case(1,-1.,.5,1.,0,0,0,1)]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((OWNER,0x80),(MODEL,0x20),(FADE,0x300),(COMMAND,0x100),(TICK,4)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,OWNER+0x24,0 if c.null_model else MODEL);put(m,MODEL,COMMAND if c.has_list else 0);put(m,FADE+0x2d8,bits(c.remaining));put(m,FADE+0x2dc,bits(c.scale));put(m,FADE+0x2ec,c.active);put(m,TICK,bits(c.tick))
 for i in range(8):put(m,COMMAND+8*i,(0xf2000000|(c.field<<12)|0x765) if i==c.index else (0xe7000000|(i<<12)|0x321));put(m,COMMAND+8*i+4,0x12345600+i)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def reference(c):
 m=fixture(c)
 if c.active:
  m[OWNER+0x13]=2;remaining=f32(c.remaining-c.tick);put(m,FADE+0x2d8,bits(remaining))
  if remaining<0:put(m,FADE+0x2ec,0);return public(m),1
  progress=f32(1.-f32(c.scale*remaining))
 else:m[OWNER+0x13]=0;progress=0.
 if c.has_list:
  tile=2-c.field//3
  while tile<0:tile+=64
  position=int(f32(f32(500.*progress)+2.));put(m,COMMAND+8*c.index,0xf2000000|((position&0xfff)<<12)|(tile&0xfff))
 return public(m),0
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,FADE));self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63 in (0x1a,0x1b):
   rs,rt=w>>21&31,w>>16&31;num,den=self.r[rs]&0xffffffff,self.r[rt]&0xffffffff;assert den
   if w&63==0x1a:
    num=(num^0x80000000)-0x80000000;den=(den^0x80000000)-0x80000000;q=abs(num)//abs(den);q=-q if (num<0)!=(den<0) else q;self.lo=q&0xffffffff;self.hi=(num-q*den)&0xffffffff
   else:self.lo,self.hi=divmod(num,den)
   self.r[0]=0;return
  super().execute(w)
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_150DFDD0']['value'],fs['func_150DFDD0']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x10D280);seen=set()
 for c in cases():
  expected,answer=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();actual=public(m.memory);assert actual==expected,(c,[(hex(k),expected.get(k),actual.get(k)) for k in expected if expected.get(k)!=actual.get(k)][:10]);assert m.r[2]==answer,(c,m.r[2],answer);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(75)),valid_finite_inputs_and_terminated_lists=True,source_installed=False);(out/'guest_150DFDD0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
