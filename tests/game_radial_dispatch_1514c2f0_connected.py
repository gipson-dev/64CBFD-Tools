"""Connect the original byte-angle lookup helper and its actual table."""
import json,struct
from tools.experiments import game_radial_dispatch_1514c2f0_match as p
from tools.tests import game_radial_dispatch_1514c2f0_oracle as g
from tools.experiments import game_radial_dispatch_1514c2f0_match as n
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
SINE_TABLE=0x8009A220
class Connected(g.Oracle):
 def hook(self,t):
  assert t in(g.CB,g.ALT);ordinal=self.cb_count;self.cb_count+=1;g.effect(self.memory,self.c,t,ordinal)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=int(ordinal!=self.c.fail)
def sample(m,a):
 a&=255;idx=64-(a&63)if a&64 else a&63;v=g.read(m,SINE_TABLE+4*idx);return v if (a&0xC0)in(0,0xC0)else v^0x80000000
def reference(initial,c):
 m=dict(initial);calls=[];angle=c.start;cb_count=0
 for i in range(max(0,c.count)):
  a=(angle-64)&255;calls.append((g.SINE,(a,)));quarter=sample(m,a);calls.append((g.SINE,(angle,)));value=sample(m,angle);target=g.read(m,g.TABLE+c.selector*4)
  if target:
   args=(1,i,g.addmul(c.x,c.radius,quarter),c.y,g.addmul(c.z,c.radius,value),c.x,c.y,c.z,angle,c.start,c.radius,c.arg8,c.arg9,c.arg10,c.arg11);calls.append((target,args));stop=cb_count==c.fail;cb_count+=1
   if stop:break
  angle=(angle+c.step)&255
 return m,calls
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>27I',rom,0x16F888);elf=(p.root/'conker/build/conker.us.elf').read_bytes();table=elf[elf_slot_offset(elf,SINE_TABLE,65*4):][:65*4];assert len(table)==260;code=dict(zip(range(g.SINE,g.SINE+108,4),helper));raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs);lookup={r[1]:r[2][1]for r in symbol_rows(elf)};syms={name:lookup[name]for es in refs.values()for _,name in es};programs=(p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms),struct.unpack_from('>96I',rom,p.ROM));count=0;visits=set()
 for angle in range(256):
  for mode in(0,1):
   c=g.Case(start=angle,step=-7,count=2,mode=mode,fail=100);models=[]
   for ws in programs:
    m=Connected(ws,c,connected=code);m.memory.update({SINE_TABLE+i:v for i,v in enumerate(table)});m.initial=dict(m.memory);want,calls=reference(m.initial,c);m.run();assert g.public(m.memory)==g.public(want)and m.calls==calls,(c,m.calls,calls);models.append(m)
   a,b,d=models;assert g.public(a.memory)==g.public(d.memory)and (b.memory,b.r,b.f,b.calls,b.trace)==(d.memory,d.r,d.f,d.calls,d.trace);visits.update(pc for pc in b.visits if g.SINE<=pc<g.SINE+108);count+=1
 r=dict(cases=count,original_sine_words=27,visited_sine_words=len(visits),all_256_input_angles_checked=True,callback_still_modeled=True,FCSR_and_hardware_not_qualified=True,source_installed=False);(p.out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
