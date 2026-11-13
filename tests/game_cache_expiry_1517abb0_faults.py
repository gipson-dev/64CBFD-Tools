from pathlib import Path
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_cache_expiry_1517abb0_guest import Case,Expiry,fixture
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;addresses={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};images=[]
for label in ('retail.o','padded.o'):
 raw,refs=payload(out/label,'func_1517ABB0');images.append(list(bound_blob(raw,refs,{s:addresses[s] for v in refs.values() for _,s in v})))
cases=(Case(0,0,0,0,0,0,0),Case(1,0,1,0,1,0,1),Case(3,2,3,2,1,3,3),Case(3,2,3,2,2,1,3),Case(3,2,3,2,3,2,3),Case(3,2,3,2,0,4,3))
cuts=delays=0
for c in cases:
 initial=fixture(c);good=Expiry(images[0],initial,c).run()
 for cut in range(good.root_accesses):
  models=[]
  for words in images:
   m=Expiry(words,initial,c);m.root_fault=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective cut',c,cut))
   models.append(m)
  assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace
  assert (models[0].current_pc,models[0].delay_of)==(models[1].current_pc,models[1].delay_of)
  cuts+=1;delays+=models[0].delay_of is not None
print(cuts,'matched retail/padded guest access-fault prefixes,',delays,'branch-delay cuts',flush=True)
