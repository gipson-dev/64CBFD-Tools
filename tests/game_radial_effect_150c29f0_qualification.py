"""Raw finite C semantics, normalized exceptional states and literal access cuts."""
from dataclasses import replace
import itertools,json
from tools.experiments import game_radial_effect_150c29f0_match as s
from tools.tests import game_radial_effect_150c29f0_oracle as g
from tools.tests import game_radial_effect_150c29f0_native as native
from tools.tests import game_radial_effect_150c29f0_callers as caller
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp as ieee
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.trace,m.calls,m.observed,m.current_pc,m.delay_of

def main():
 g.s=native.s=caller.s=s;programs=s.programs();assert programs[0]==programs[2]
 count=0
 for c in g.cases():
  initial=g.fixture(c)
  for words in programs:m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c)
  count+=1
 exceptional=0
 for value,slot,rule in itertools.product((0,0x80000000,1,0x7f7fffff,0x7f800000,0xff800000,0x7f800001,0x7fc30002),range(7),('left','right')):
  c=g.Case();r=list(c.randoms);p=list(c.position)
  if slot<3:r[(1,3,4)[slot]]=value
  else:p[slot-3]=value
  c=replace(c,randoms=tuple(r),position=tuple(p));g.fp=lambda a,b,op:ieee(a,b,op,rule);initial=g.fixture(c);states=[]
  for words in (programs[0],programs[2]):m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c);states.append(state(m))
  assert states[0]==states[1];exceptional+=1
 boundaries=[]
 for rule in ('left','right'):
  c=g.Case(randoms=(0,0x7fc00001,0xffffffff,0x3e800000,0x3f400000,0x80000000),position=(0x3f800000,0xc0200000,0x7fc30002,0x40400000))
  g.fp=lambda a,b,op:ieee(a,b,op,rule);initial=g.fixture(c);obs=[]
  for i,words in enumerate(programs):
   m=g.Oracle(words,initial,c);m.run();obs.append(m.observed[0][:4].hex())
   if i!=1:g.verify(m,initial,c)
  assert obs[0]==obs[2] and obs[0]!=obs[1];boundaries.append(dict(rule=rule,retail=obs[0],raw=obs[1],normalized=obs[2]));exceptional+=1
 prefixes=0
 for c in (g.Case(),g.Case(mutation=1,phase=8),g.Case(randoms=(0,0x7fc00001,1,0x3e800000,0x3f400000,2),position=(0x3f800000,0xc0200000,0x7fc30002,0x40400000))):
  g.fp=lambda a,b,op:ieee(a,b,op,'left');initial=g.fixture(c);m=g.Oracle(programs[0],initial,c);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words in (programs[0],programs[2]):
    m=g.Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Literal instruction access cut did not fire')
    states.append(state(m))
   assert states[0]==states[1];prefixes+=1
 g.fp=lambda a,b,op:ieee(a,b,op,'left')
 native.main(controls_override={'owner':('position[0xC]','position[0xB]')});n=json.loads((s.OUT/'native-report.json').read_text());n.pop('private_uninstalled');n.update(current_semantic_source=True,source_installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()));(s.OUT/'native-report.json').write_text(json.dumps(n,indent=2)+'\n')
 caller.main();c=json.loads((s.OUT/'caller-report.json').read_text());c.pop('private_uninstalled');c['streams']=3;c['retail_normalized_target_literal_equality']=True;c['raw_stack_not_credited']=True;(s.OUT/'caller-report.json').write_text(json.dumps(c,indent=2)+'\n')
 report=dict(finite_cases=count,finite_streams=3,exceptional_cases=exceptional,exceptional_streams=2,ordered_nan_boundaries=boundaries,literal_state_access_prefixes=prefixes,trig_original_words=27,hardware_fcsr_not_claimed=True,private_home_move_bounded_to_valid_owner_domain=True)
 (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
