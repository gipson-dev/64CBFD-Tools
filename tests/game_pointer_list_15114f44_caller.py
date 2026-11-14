from tools.tests.game_pointer_list_15114f44_common import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
callsite=0x15100000;end=callsite+8;inst=(0x0c000000|((entry>>2)&0x03ffffff),0)
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==entry:self.calls.append((t,tuple(self.arguments(3))));return
  return super().record_call(t)
count=0
for mode,counts,pattern in itertools.product((0,0x12,0x13,0x36,0x37),((-1,0),(0,1),(1,1),(3,1)),(0,10)):
 m=fixture(mode,counts,pattern);want,calls,trap=model(m,args,True,0);runs=[]
 for label in ('retail','raw','guarded'):
  q=CallerOracle(programs[label],m.copy(),args,True,0);code=dict(q.code);code.update(zip(range(callsite,end,4),inst));code[end]=0;q.code=WindowCode(code,q);q.code.ends=(end,);q.entry=callsite;q.before=q.r[:]
  try:q.run();raise AssertionError('caller did not stop')
  except WindowBoundary:pass
  assert public(q.memory)==want,(mode,counts,pattern,label);assert q.calls[0]==(entry,args) and len(q.calls)==1+calls
  assert all(q.r[i]==q.before[i] for i in (*range(16,24),28,29,30));runs.append(q)
 assert trace(runs[0])==trace(runs[1])==trace(runs[2]);count+=1
print(json.dumps(dict(synthetic_caller_cases=count,direct_jal_assembly_search_hits=0,full_caller_coverage=False,uncredited=True)),flush=True)
