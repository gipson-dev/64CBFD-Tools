from tools.tests.game_selector_mask_1515942c_common import *
rom=(conker/'conker.us.bin').read_bytes();helper_words=struct.unpack_from('>23I',rom,0x17c190);code=dict(zip(range(HELPER,HELPER+92,4),helper_words));count=diff=0
for i in range(256):
 for found in (False,True):
  c=Scenario(tuple((-1,0,1,2,31)[(i+j)%5] for j in range(5)),tuple((i*13+j*31)&255 for j in range(5)),found,0);m=fixture(c);put(m,NODE+0x14,0);put(m,NODE+0x1c,0x13 if found else 0x12,2);runs=[]
  for name in ('retail','candidate'):
   q=Oracle(programs[name],m.copy(),c,connected=code).run();assert q.r[2]==result(c),(i,found,name);runs.append(q)
  assert public(runs[0].memory)==public(runs[1].memory)
  diff+=int(tr(runs[0])!=tr(runs[1]));count+=1
assert count==512 and diff==0
print(json.dumps(dict(cases_per_stream=count,original_lookup_words=23,public_access_order_differences=diff,uncredited=True)),flush=True)
