from tools.tests.game_actor_associated_1511473c_common import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
window=0x151142bc;end=0x151142c8;rom=(conker/'conker.us.bin').read_bytes();inst=struct.unpack_from('>3I',rom,0x14176c)
assert inst==(0x03ce2021,0x0d4451cf,0x02602825)
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==entry:self.calls.append((t,tuple(self.arguments(2))));return
  return super().record_call(t)
count=0
for index,n,flag,match,mode in itertools.product((-1,0,1),(-1,2),(0,1),(False,True),(0,1)):
 m=fixture(index,n,32767,0.5,1.5,flag,match,mode);want=model(m,index,n,mode,True);runs=[]
 for label in ('retail','raw','guarded'):
  q=CallerOracle(programs[label],m.copy(),(0,0),mode);code=dict(q.code);code.update(zip(range(window,end,4),inst));code[end]=0;q.code=WindowCode(code,q);q.code.ends=(end,);q.entry=window;q.r[30]=actor-0x32c;q.r[14]=0x32c;q.r[19]=index&0xffffffff;q.before=q.r[:]
  try:q.run();raise AssertionError('caller did not stop')
  except WindowBoundary:pass
  assert public(q.memory)==want,(label,index,n,flag,match,mode);assert q.calls[0]==(entry,(actor,index&0xffffffff));assert len(q.calls)==1+int(index<n);runs.append(q)
 assert runs[0].trace==runs[1].trace==runs[2].trace;count+=1
print(json.dumps(dict(caller_window_cases=count,window='0x151142bc..0x151142c8',parent_not_fully_executed=True,uncredited=True)),flush=True)
