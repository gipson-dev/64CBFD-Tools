from pathlib import Path
import sys,json,random,importlib.util
from tools.experiments import game_position_interpolation_match as source
root=source.root;p=source.out
from tools.tests import game_position_interpolation_guest as g
from tools.tests.test_game_queued_segment_writer import STACK

def main():
 class Stop(Exception): pass
 class Model(g.Model):
  def __init__(self,*args,cut=None,**kwargs):self.cut=cut;self.access_count=0;super().__init__(*args,**kwargs)
  def check(self):
   if self.recording:
    if self.access_count==self.cut:raise Stop()
    self.access_count+=1
  def get(self,a,n):self.check();return super().get(a,n)
  def put(self,a,v,n):self.check();return super().put(a,v,n)
 def run(words,m,actor,cut=None):
  model=Model(words,m,entry=g.entry,arguments=(actor,),cut=cut)
  try:model.run();stopped=False
  except Stop:stopped=True
  return stopped,model.access_count,model.memory,model.events
 rng=random.Random(0x150be2);total=0
 for case in range(12):
  actor=(0x20000,0x800A0068-0x10,0x800BE9E4-0x10)[case%3];values=[rng.randrange(-32768,32768) for _ in range(8)];m=g.fixture(actor,values,(0,1,2,-1)[case%4],(0,0x3f000000,0xbf000000,0x3f800000)[case%4])
  baseline=run(g.ret,m,actor);assert not baseline[0]
  for cut in range(baseline[1]+1):
   x=run(g.ret,m,actor,cut);y=run(g.candidate,m,actor,cut);assert x==y,(case,cut,x[:2],y[:2]);total+=1
 print(json.dumps(dict(fault_prefixes=total,cases=12,scope='bounded access model; finite values only; no FPU exception or host C fault-semantics claim'),indent=2))


if __name__ == "__main__":main()
