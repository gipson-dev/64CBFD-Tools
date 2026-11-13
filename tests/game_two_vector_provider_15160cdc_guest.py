from pathlib import Path
import itertools,sys
from tools.experiments import game_two_vector_provider_15160cdc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_two_vector_effect_match as src
from tools.tests.game_two_vector_effect_oracle import Case,EffectOracle,fixture,provider_reference,public,OWNER,STACK,FACTORY,COPY
from tools.tests.test_game_point_transform_match import put
SYMS={'func_151602C0':FACTORY,'memcpy':COPY}
def run():
 programs=[bound_blob(*payload(out/x,'func_15160CDC'),SYMS) for x in ('retail.o','after.o','generic.o','generated.o')];assert all(p==programs[0] for p in programs)
 count=0;visits=set()
 for flag0,flag1,duration,owner,allocated,mode,alias in itertools.product((0,1,255),(0,1,255),(0,0xffff8000,0xffffffff,32767),(0,OWNER),(False,True),(0,1),(False,True)):
  c=Case(owner=owner,allocated=allocated,mode=mode,alias_output=alias);initial=fixture(c);args=(owner,255,src.VEC_A,src.VEC_B,0x80000000,255,duration,1,2,3,4,flag0,0xa5,flag1,255,0xffffffff)
  for i,v in enumerate(args[4:],4):put(initial,STACK+i*4,v)
  expected,calls,obs,result=provider_reference(initial,args,c,STACK)
  for words in programs:
   m=EffectOracle(words,initial.copy(),c,entry=src.EFFECT,arguments=args[:4]).run();visits.update(m.visits)
   assert (public(m.memory),m.calls,m.factory_observations,m.r[2])==(public(expected),calls,obs,result),(flag0,flag1,duration,owner,allocated,mode,alias)
  count+=1
 assert set(range(src.EFFECT,src.EFFECT+340,4))<=visits
 print(count,'guest provider cases per stream; every retail instruction visited; allocator and copy modeled')
