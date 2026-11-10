"""Compiled mistakes must produce normal, observable float/alias witnesses."""
import json
from tools.experiments import game_paired_float_approach_1505a250_match as p
from tools.tests import game_paired_float_approach_1505a250_oracle as g
def mutants(source):
 changes={
 'wrong-x-delta':('target_x - *x','target_x + *x'),
 'wrong-z-delta':('target_z - *z','target_z + *z'),
 'zero-test-disjunction':('(delta_x == 0.0f) && (delta_z == 0.0f)','(delta_x == 0.0f) || (delta_z == 0.0f)'),
 'missing-timestep':('rate *= D_800D1550[0];','rate = rate;'),
 'wrong-length-sum':('delta_x * delta_x + delta_z * delta_z','delta_x * delta_x - delta_z * delta_z'),
 'missing-square-root':('sqrtf(delta_x * delta_x + delta_z * delta_z)','(delta_x * delta_x + delta_z * delta_z)'),
 'wrong-x-normalization':('delta_x / distance * rate','delta_x * distance * rate'),
 'missing-x-absolute':('fabsf(delta_x / distance * rate)','(delta_x / distance * rate)'),
 'missing-z-absolute':('fabsf(delta_z / distance * rate)','(delta_z / distance * rate)'),
 'wrong-x-clamp':('if (*x < target_x)','if (*x > target_x)'),
 'wrong-z-direction':('if (delta_z >= 0.0f)','if (delta_z <= 0.0f)'),
 'missing-x-clamp-store':('*x = target_x;','*x = *x;'),
 'missing-z-clamp-store':('*z = target_z;','*z = *z;')}
 result={}
 for label,(a,b)in changes.items():assert a in source;result[label]=source.replace(a,b)
 result['cached-second-output']=source.replace('    f32 delta_x;','    f32 initial_z = *z;\n    f32 delta_x;').replace('*z = *z + step_z;','*z = initial_z + step_z;').replace('*z = *z - step_z;','*z = initial_z - step_z;')
 begin=source.index('    if (delta_x >=');middle=source.index('    if (delta_z >=');first=source[begin:middle];second=source[middle:source.rfind('}')]
 result['reversed-output-order']=source[:begin]+second+first+'}'
 late=source.replace('    f32 delta_x;','    f32 original_rate = rate;\n    f32 delta_x;').replace('    step_z = fabsf(delta_z / distance * rate);\n','').replace('    if (delta_z >=','    step_z = fabsf(delta_z / distance * (original_rate * D_800D1550[0]));\n    if (delta_z >=')
 result['late-timestep-reread']=late
 result['zero-rate-shortcut']=source.replace('    delta_x =','    if (rate == 0.0f) { return; }\n    delta_x =',1)
 return result
def different(actual,expected,c):
 px,pz=g.pointers(c);modified=set()
 for a in(px,pz):
  if g.canonical(g.read(actual,a))!=g.canonical(g.read(expected,a)):return True
  modified.update(range(a,a+4))
 return any(actual[a]!=v for a,v in g.public(expected).items()if a not in modified)
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text();source=p.BASE;cs=[g.Case(),g.Case(target_x=g.bits(20.)),g.Case(timestep=g.bits(.5)),g.Case(alias=1),g.Case(alias=1,target_z=g.bits(10.),rate=g.bits(100.)),g.Case(rate=g.bits(100.)),g.Case(alias=2),g.Case(alias=3),g.Case(rate=0,x=1,z=0),g.Case(x=g.bits(-20.),z=g.bits(10.))];found={}
 for name,mutant in mutants(source).items():
  obj,_=p.compile_owner(p.root,p.out,p.proposal(old,mutant),'negative-'+name);ws=g.words(obj)
  for i,c in enumerate(cs):
   m=g.Oracle(ws,g.fixture(c),c);m.run();expected,_=g.reference(m.initial,c)
   if different(m.memory,expected,c):found[name]=dict(case=i,normal_completion=True,execution_errors=0);break
  assert name in found,('No functional witness',name);print(name,json.dumps(found[name]),flush=True)
 result=dict(controls=len(found),effective_compiled_controls=found);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':main()
