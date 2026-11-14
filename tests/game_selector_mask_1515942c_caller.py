from tools.tests.game_selector_mask_1515942c_common import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
rom=(conker/'conker.us.bin').read_bytes();caller=0x1507f128;end=0x1507f144;offset=0xac5d8;body=struct.unpack_from('>7I',rom,offset);assert body[5]==0x0d45650b
helper=struct.unpack_from('>23I',rom,0x17c190);code=dict(zip(range(HELPER,HELPER+92,4),helper))
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==entry:self.calls.append((t,tuple(self.arguments(6))));return
  return super().record_call(t)
count=diff=0
for i,found in itertools.product(range(256),(False,True)):
 c=Scenario((0,0,-1,-1,-1),tuple((i*13+j*31)&255 for j in range(5)),found,0);m=fixture(c);put(m,NODE+0x14,0);put(m,NODE+0x1c,0x13 if found else 0x12,2);runs=[]
 for name in ('retail','candidate'):
  q=CallerOracle(programs[name],m.copy(),c,connected=code);words=dict(q.code);words.update(zip(range(caller,end,4),body));words[end]=0;q.code=WindowCode(words,q);q.code.ends=(end,);q.entry=caller;q.r[25]=0;q.r[9]=ACTOR;q.r[10]=q.r[11]=0xffffffff;q.before=q.r[:]
  try:q.run();raise AssertionError('caller did not stop')
  except WindowBoundary:pass
  assert q.calls[0]==(entry,(ACTOR,0,0,0xffffffff,0xffffffff,0xffffffff));assert q.r[2]==result(c),(i,found,name);runs.append(q)
 diff+=int(tr(runs[0])!=tr(runs[1]));assert public(runs[0].memory)==public(runs[1].memory);count+=1
assert count==512 and diff==0
print(json.dumps(dict(cases_per_stream=count,original_caller_window_words=7,original_lookup_words=23,public_access_order_differences=diff,uncredited=True)),flush=True)
