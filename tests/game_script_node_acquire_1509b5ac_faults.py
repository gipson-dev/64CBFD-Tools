"""Compare every modeled memory-access prefix of retail and padded bodies."""
import struct
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_script_node_acquire_1509b5ac_guest import Case,Loader,fixture
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete

addresses={row[1]:row[2][1] for row in symbol_rows((source.ROOT/'conker/build/conker.us.elf').read_bytes())}
images=[]
for label in ('durable-retail.o','durable-padded.o'):
 raw,refs=payload(source.OUT/label,source.NAME)
 images.append(list(bound_blob(raw,refs,{s:addresses[s] for values in refs.values() for _,s in values})))
cases=(Case(7,0,False,0,False,False,0),Case(7,0,False,0x400,True,False,0),
       Case(7,1,False,0x400,False,True,1),Case(7,1,False,0x1400,False,False,6),
       Case(7,1,True,0x1000,False,False,0),Case(7,1,True,0x1800,False,False,0))
cuts=delays=0
for c in cases:
 initial=fixture(c);good=Loader(images[0],initial,c).run()
 for cut in range(good.root_accesses):
  models=[]
  for words in images:
   m=Loader(words,initial,c);m.root_fault=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective prefix',c,cut))
   models.append(m)
  assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace
  assert (models[0].current_pc,models[0].delay_of)==(models[1].current_pc,models[1].delay_of)
  delays+=models[0].delay_of is not None;cuts+=1
print(cuts,'matched retail and padded guest access-fault prefixes;',delays,'delay-slot cuts',flush=True)
