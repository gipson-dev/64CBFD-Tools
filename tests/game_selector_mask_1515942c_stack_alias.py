from tools.tests.game_selector_mask_1515942c_common import *
count=0;diff=[]
for delta,selectors,mutate in itertools.product(range(-8,9),((-1,-1,-1,-1,-1),(0,0,0,0,0),(-32768,31,32,32767,-33)),(0,1)):
 c=Scenario(selectors,(0,0,0,0,0),True,mutate);m=fixture(c);data=STACK-0x40+0x37-0x2c+delta;put(m,NODE+0x10,data);runs=[]
 for name in ('retail','candidate'):
  q=Oracle(programs[name],m.copy(),c).run();runs.append(q)
 if (runs[0].r[2],public(runs[0].memory),runs[0].trace)!=(runs[1].r[2],public(runs[1].memory),runs[1].trace):diff.append((delta,selectors,mutate,runs[0].r[2],runs[1].r[2]))
 count+=1
assert count==102 and not diff
print(json.dumps(dict(private_stack_alias_cases=count,full_access_and_return_differences=len(diff),examples=diff[:4],uncredited=True)),flush=True)
