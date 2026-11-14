"""Private-home redirects and public-state access prefixes for all three streams."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,os
from tools.tests import game_direction_strip_151a7d6c_oracle as b
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

@dataclass(frozen=True)
class Case(b.Case):
 private:int=0
 alternate_camera:int=0x91000

class Oracle(b.Oracle):
 def __init__(self,words,initial,c):
  self.home_offsets={'camera':words[31]&65535,'last':words[39]&65535};super().__init__(words,initial,c)
 def hook(self,t):
  super().hook(t);c=self.case;frame=b.STACK+c.phase-200
  if c.private==1 and t==b.ALLOC:b.put(self.memory,b.STACK+c.phase+8,0xabcdffff)
  if c.private==2 and t==b.TEXTURE:b.put(self.memory,frame+self.home_offsets['last'],0,2)
  if c.private==3 and t==b.COLOR:b.put(self.memory,self.roles['cursor'],b.BUFFER+256)
  if c.private==4 and t==b.PROJECT:b.put(self.memory,frame+self.home_offsets['camera'],c.alternate_camera)
  if c.private==5 and t==b.ALLOC:
   b.put(self.memory,b.STACK+c.phase,0xdead0000);b.put(self.memory,b.STACK+c.phase+4,0xdead1000)

def fixture(c):
 m=b.fixture(c);b.store(m,c.alternate_camera,(-3.5,2.25,1.5));return m

def expected(initial,c):
 if c.private==3:
  # The escaped cursor is redirected earlier than the projection provider;
  # no intervening target instruction accesses that cursor.
  from dataclasses import replace
  return b.reference(initial,replace(c,mutation=c.mutation|4))
 return b.reference(initial,c)

def projection(machine):return b.public(machine.memory),machine.calls,machine.observed

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/'conker/build/game-direction-strip-151a7d6c-screen';symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_151A7D6C'),symbols) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
 full=0
 for c in b.cases():
  initial=b.fixture(c);memory,calls,obs,value=b.reference(initial,c)
  for words in programs:
   machine=b.Oracle(words,initial,c);before=machine.r[:];before_f=machine.f[:];machine.run()
   assert (b.public(machine.memory),machine.calls,machine.observed,machine.r[2])==(b.public(memory),calls,obs,value),c
   assert all(machine.r[i]==before[i] for i in (*range(16,24),28,29,30,31)),c
   assert machine.f[20:]==before_f[20:],c
  full+=1
 private=0;effective=set()
 for mode,mutation,phase in itertools.product(range(1,6),(0,3),(0,8)):
  c=Case(private=mode,mutation=mutation,phase=phase);initial=fixture(c);memory,calls,obs,value=expected(initial,c)
  for words in programs:
   machine=Oracle(words,initial,c);machine.run();assert (b.public(machine.memory),machine.calls,machine.observed,machine.r[2])==(b.public(memory),calls,obs,value),(c,programs.index(words))
  if mode in (2,3,4):
   from dataclasses import replace
   ordinary=b.reference(initial,replace(c,private=0))[0]
   if b.public(memory)!=b.public(ordinary):effective.add(mode)
  private+=1
 assert effective=={2,3,4}
 prefixes=0
 cases=(Case(flags=0),Case(success=0),Case(count=0),Case(count=2),Case(shape=2,count=2),Case(mutation=7),Case(private=2),Case(private=4))
 for c in cases:
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for words in programs:
    machine=Oracle(words,initial,c);machine.cut=cut
    try:machine.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing fired access boundary')
    states.append(projection(machine))
   assert states[0]==states[1]==states[2],(c,cut)
   prefixes+=1
 report=dict(three_stream_cases=full,private_home_cases=private,effective_redirect_modes=sorted(effective),public_state_access_prefixes=prefixes,callee_saved_gpr_fpr_preserved=True,raw_private_register_state_not_compared=True,providers_modeled=True)
 (out/'extended-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
