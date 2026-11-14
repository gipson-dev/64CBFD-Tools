from tools.tests.game_selector_mask_1515942c_common import *
count=diff=0
vals=(-32768,-33,-1,0,1,2,31,32,32767)
for i in range(1024):
 v=tuple(vals[((i>>(2*j))+(i*(j+1)))%len(vals)] for j in range(5));fields=tuple((i*(13+2*j)+j*31)&255 for j in range(5))
 for found,mutate in itertools.product((False,True),(0,1)):
  c=Scenario(v,fields,found,mutate);m=fixture(c);runs=[]
  for name in ('retail','candidate'):
   q=Oracle(programs[name],m.copy(),c).run();assert q.r[2]==result(c),(name,c,q.r[2],result(c));assert len(q.calls)==1 and q.calls[0][1][:2]==(NODE,0x13);runs.append(q)
  if tr(runs[0])!=tr(runs[1]):diff+=1
  assert public(runs[0].memory)==public(runs[1].memory);count+=1
assert count==4096 and diff==int(__import__('os').environ.get('SELECTOR_EXPECTED_TRACE_DIFFS','0'))
print(json.dumps(dict(cases_per_stream=count,public_memory_and_return_agree=True,public_access_order_differences=diff,uncredited=True)),flush=True)
