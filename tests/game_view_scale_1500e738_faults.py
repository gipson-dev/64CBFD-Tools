from pathlib import Path
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_view_scale_1500e738_guest import ENTRY,View,fixture
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;addresses={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};images=[]
for label in ('retail.o','padded.o'):
 raw,refs=payload(out/label,'func_1500E738');images.append(list(bound_blob(raw,refs,{s:addresses[s] for v in refs.values() for _,s in v})))
base,data=sections(root/'conker/build/conker.us.elf')['.game_data'];table=data[0x800961D0-base:0x800961D0-base+64]
cuts=delays=0
for state,mode in ((0,1),(1,2),(2,3),(3,5),(4,9),(0xFFFFFFFF,255)):
 initial=fixture(state,mode,table,0x800961D0);good=View(images[0],initial,ENTRY).run()
 for cut in range(good.root_accesses):
  models=[]
  for words in images:
   m=View(words,initial,ENTRY);m.root_fault=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective cut',state,mode,cut))
   models.append(m)
  assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace
  assert (models[0].current_pc,models[0].delay_of)==(models[1].current_pc,models[1].delay_of)
  cuts+=1;delays+=models[0].delay_of is not None
print(cuts,'matched retail/padded guest access-fault prefixes,',delays,'branch-delay cuts',flush=True)
