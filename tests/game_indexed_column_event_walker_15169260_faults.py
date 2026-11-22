"""Fault cuts at public and named-frame accesses, with private-frame projection."""
from pathlib import Path
from dataclasses import replace
import json,sys
from tools.experiments import game_indexed_column_event_walker_15169260_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_indexed_column_event_walker_15169260_guest as p
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class PublicOracle(p.Oracle):
 def __init__(self,*args,**kwargs):
  self.observable_accesses=0;self.observable_cut=None
  super().__init__(*args,**kwargs)
 def visible(self,a):
  h=self.target_home
  return not p.STACK-4096<=a<p.STACK+1024 or h<=a<h+64 or h-24<=a<h-20 or h-8<=a<h-4
 def boundary(self,a):
  if self.own_instruction and self.visible(a):
   if self.observable_accesses==self.observable_cut:raise AccessBoundary
   self.observable_accesses+=1
 def get(self,a,n):self.boundary(a);return super().get(a,n)
 def put(self,a,v,n):
  if self.recording:self.boundary(a)
  return super().put(a,v,n)
def prefix(m):
 return({a:v for a,v in m.memory.items()if m.visible(a)},[e for e in m.trace if m.visible(e[1])],m.calls,m.observations,m.f[20:])
def main():
 paths=[out/'sdk-frame-last/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];helpers=p.helper_code();count=0
 cases=(p.Case(),replace(p.Case(),empty=True,phase=8),replace(p.Case(),pattern=0,mode=31),replace(p.Case(),pattern=1,mode=31),replace(p.Case(),real_helpers=True,opcode=15),replace(p.Case(),mode=32),replace(p.Case(),list_home=True,opcode=2,mode=32),replace(p.Case(),count=0))
 for c in cases:
  full=[]
  for path in paths:
   m=PublicOracle(p.words(path),p.fixture(c),c,connected=helpers if c.real_helpers else None);m.run();p.check(m,c);full.append(m)
  assert len({m.observable_accesses for m in full})==1,(c,[m.observable_accesses for m in full])
  assert prefix(full[0])==prefix(full[1])==prefix(full[2]),('Complete observable state',c)
  for cut in range(full[0].observable_accesses):
   states=[]
   for path in paths:
    m=PublicOracle(p.words(path),p.fixture(c),c,connected=helpers if c.real_helpers else None);m.observable_cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing observable access boundary')
    states.append(prefix(m))
   assert states[0]==states[1]==states[2],(c,cut);count+=1
 r=dict(observable_access_fault_triples=count,discriminating_cases=len(cases),public_and_named_frame_prefixes_equal=True,
  projection='All non-stack bytes, incoming 64 bytes, row H-24 and counter H-8; ordered accesses, calls, observations and saved FPR.',
  limits='Private save slots, helper return addresses, GPR role identity, PCs, FCSR, cycle timing, provider-internal faults and recursive provider faults are not equated. Completed saved GPR/SP/RA ABI is checked separately.',source_installed=packet.installed(),matching_credit=0)
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
