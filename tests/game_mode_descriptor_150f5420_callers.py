from pathlib import Path
import importlib.util,itertools,json
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
import struct
root=Path.cwd();out=root/'conker/build/game-mode-descriptor-150f5420-screen'
from tools.tests import game_mode_descriptor_150f5420_behavior as b
g=b.g;g.rom=(root/'conker/conker.us.bin').read_bytes()
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
programs=[bound_blob(*payload(out/f,'func_150F5420'),symbols) for f in ('retail.o','selected.o','guarded.o')]
caller_count=0
for which,mode,first,remaining,third,consumed,result,phase in itertools.product((0,1),(0,1,2,3,127,128,255),(0,0xffffffff),(17,0xffffffff),(0,0x10000),(0,0xffffffff),(0,g.OUTPUT),(0,8)):
 signed=b.u32((mode^128)-128);args=(first,b.u32(remaining-consumed-third-first),third,signed)
 c=b.Case(args,result,phase,seed=mode,connected=True);initial=b.fixture(c);ptr=0x60000;initial.update({ptr+i:0 for i in range(16)});initial[ptr+5]=mode
 if which==0:pc,end,off,n=0x15026008,0x150265b4,0x534b8,9
 else:pc,end,off,n=0x1502a650,0x1502a88c,0x57b00,8;put(initial,g.STACK+phase+0xdc,consumed)
 window=list(struct.unpack_from('>%dI'%n,g.rom,off));expected,calls,obs=b.reference(initial,c)
 for program in programs:
  code=g.helpers();code.update(zip(range(b.ENTRY,b.ENTRY+368,4),program));code[end]=0
  m=b.Oracle(window,initial,c,entry=pc,connected=code)
  if which==0:m.r[16]=first;m.r[17]=remaining;m.r[24]=consumed;m.r[6]=third;m.r[18]=ptr;m.r[2]=0x18;m.r[1]=0x18
  else:m.r[16]=ptr;m.r[3]=remaining;m.r[4]=first;m.r[6]=third
  m.code=WindowCode(m.code,m);m.code.ends=(end,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not reach boundary')
  assert (g.public(m.memory),m.calls,m.observed,m.r[2])==(g.public(expected),[(b.ENTRY,args)]+calls,obs,1),(which,c,m.calls)
 caller_count+=1
prefix_count=0
for mode,result,connected,mutation in itertools.product((0,1,2,3),(0,g.OUTPUT),(False,True),(0,1)):
 c=b.Case((0xffffffff,0x10000,0x80000000,mode),result,mutation=mutation,connected=connected);initial=b.fixture(c)
 complete=b.Oracle(programs[0],initial,c,connected=g.helpers() if connected else None);complete.run()
 for cut in range(complete.all_accesses):
  states=[]
  for program in programs:
   m=b.Oracle(program,initial,c,connected=g.helpers() if connected else None);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError('prefix did not trigger')
   states.append(g.state(m))
  assert states[0]==states[1]==states[2]
  prefix_count+=1
print(json.dumps(dict(original_caller_window_cases=caller_count,caller_executions=caller_count*3,guest_access_prefixes=prefix_count,callee_executions=prefix_count*3,full_caller_runtime_claimed=False,portable_fault_behavior_claimed=False)),flush=True)
