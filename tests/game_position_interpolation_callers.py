from pathlib import Path
import sys,struct,random,json,importlib.util
from tools.experiments import game_position_interpolation_match as source
root=source.root;p=source.out
from tools.tests import game_position_interpolation_guest as g
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK

def main():
 class Window(g.Model):
  def record_call(self,target):
   assert target==g.entry,(hex(target),hex(self.r[4]));self.calls.append((target,self.r[4]))
  def run_window(self,words,start,memory,actor):
   raise NotImplementedError
 rom=(root/'conker/conker.us.bin').read_bytes();rng=random.Random(0x15113e54);results={}
 for start in (0x15113ee0,0x15113fb8):
  off=start-0x15000000+0x2d4b0;window=list(struct.unpack_from('>4I',rom,off));assert window==[0x8e190038,0x02002025,0x0320f809,0]
  def run(words,initial,actor):
   connected=dict(zip(range(g.entry,g.entry+336,4),words));connected[start+16]=0x02e00008;connected[start+20]=0
   m=Window(window,initial,entry=start,arguments=(0,),connected=connected,tail=True);m.r[16]=m.before[16]=actor;m.r[23]=m.before[23]=0xdead0000;m.run();assert m.calls==[(g.entry,actor)],m.calls
   external={a:b for a,b in m.memory.items() if not STACK-0x700<=a<STACK+0x180}
   return external,[e for e in m.events if e[0] in ('R','W') and not STACK-0x700<=e[1]<STACK+0x180],m.calls
  for k in range(100):
   actor=0x20000;values=[rng.randrange(-32768,32768) for _ in range(8)];m=g.fixture(actor,values,(0,1,2,-1)[k%4],(0,0x3f000000,0xbf000000,0x3f800000)[k%4]);put(m,actor+0x38,g.entry)
   retail=run(g.ret,m,actor);candidate=run(g.candidate,m,actor);patched=run(g.patched,m,actor)
   assert retail==candidate==patched,(hex(start),k)
  results[hex(start)]=100
 print(json.dumps(dict(windows=results,notes='four original instructions per window; bounded finite data; model return trampoline; not complete parent execution'),indent=2))


if __name__ == "__main__":main()
