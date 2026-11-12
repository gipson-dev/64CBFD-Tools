"""Run the original damping and sine helpers, with the current retail table."""
import itertools,json,struct
from tools.tests import game_oscillating_effect_151db97c_oracle as g
from tools.match_progress import load_elf_functions
from tools.experiments.game_sequence_direction_1501fe68_match import elf_slot_offset
rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.root/'conker/build/conker.us.elf').read_bytes()
damp=struct.unpack_from('>16I',rom,0x15edc8);sine=struct.unpack_from('>27I',rom,0x16f888)
live,_,_=load_elf_functions(str(g.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
assert live['func_15131918']==list(damp) and live['func_151423D8']==list(sine)
TABLE=0x8009a220;table=struct.unpack_from('>65I',elf,elf_slot_offset(elf,TABLE,260))
def actual_sine(arg):
 idx=64-(arg&63) if arg&64 else arg&63
 value=table[idx]
 return value if (arg&0xc0) in (0,0xc0) else value^0x80000000
def reference(c,initial):
 m=dict(initial);calls=[]
 if m[g.RECORD+0xa8]&2:
  damping=g.read(m,g.RECORD+0xac);calls.append((g.DAMP,(g.RECORD+0x58,damping)))
  tick=((g.read(m,g.TICK)^0x80000000)-0x80000000)
  for _ in range(max(0,tick)):
   for off in (0x58,0x60):g.put(m,g.RECORD+off,g.fp(g.read(m,g.RECORD+off),damping,'mul'))
 if m[g.RECORD+0xa8]&1:
  for i in range(3):m[g.RECORD+0xb0+i]=(m[g.RECORD+0xb0+i]+m[g.RECORD+0xb3+i]*g.read(m,g.TICK))&255
  values=[]
  for i in range(3):
   arg=(m[g.RECORD+0xb0+i]-64)&255;calls.append((g.SINE,(arg,)));values.append(actual_sine(arg))
  for i in range(3):g.put(m,g.RECORD+0x4c+4*i,g.fp(g.read(m,g.RECORD+0xb8+4*i),values[i],'mul'))
 return m,calls
class Connected(g.Oracle):
 def __init__(self,words,c):
  super().__init__(words,c)
  self.code.update(dict(zip(range(g.DAMP,g.DAMP+64,4),damp)))
  self.code.update(dict(zip(range(g.SINE,g.SINE+108,4),sine)))
  for i,v in enumerate(table):g.put(self.memory,TABLE+4*i,v)
  for off,val in ((0x58,2.),(0x5c,-3.),(0x60,4.)):g.put(self.memory,g.RECORD+off,g.bits(val))
  self.initial=dict(self.memory)
 def execute(self,w):
  if w>>26==17 and (w>>21)&31==16 and (w&63)==7:self.f[(w>>6)&31]=self.f[(w>>11)&31]^0x80000000
  else:super().execute(w)
def cases():
 for flags,tick,seed,phase in itertools.product((0,1,2,3),(0xffffffff,0,1,2),range(3),(0,8)):
  yield g.Case(flags,0,tick,seed,phase)
def main():
 retail=struct.unpack_from('>75I',rom,0x208e2c);candidate=g.words('independent-selected');seen=set();count=0
 for c in cases():
  for ws in (retail,candidate):
   m=Connected(ws,c);m.run();expected,calls=reference(c,m.initial)
   assert (g.public(m.memory),m.calls,m.r[2])==(g.public(expected),calls,1),(c,m.calls,calls)
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
  count+=1
 report=dict(cases=count,helpers=['retail func_15131918','retail func_151423D8'],helpers_match_current_elf=True,damp_words_visited=sum(g.DAMP+4*i in seen for i in range(16)),sine_words_visited=sum(g.SINE+4*i in seen for i in range(27)),valid_disjoint_record_only=True,source_installed=False)
 (g.out/'connected_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
