"""Independently audit every incoming cut value and the complete reachable CFG."""
from pathlib import Path
from copy import deepcopy
import importlib.util,inspect,json,sys
from tools.tests import game_side_ring_renderer_1519fe6c_composition as generic
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_side_ring_renderer_1519fe6c_coverage import static

from tools.tests import game_ribbon_renderer_151a3be4_proof as p
O=p.O
e=p.e;COUNTS=p.COUNTS;SYNC=p.SYNC
for function in(generic.need,generic.writes,generic.decode,generic.ObservedList,generic.tracked,generic.value):exec(inspect.getsource(function),globals())
text=inspect.getsource(generic.run).replace('g.COUNTS','COUNTS').replace('g.SYNC','SYNC').replace('-95','-93')
exec(text,globals())
text=inspect.getsource(generic.observe).replace("('STACK',-240)","('STACK',-296)").replace('opening.saved(s)','p.saved(s)')
exec(text,globals())

def atom(v):
 if not isinstance(v,tuple):return None
 if len(v)==1 and v[0]!='RETURN':return v
 if v[0]=='FCSR':return('FCSR',)
 return None

def narrow(v,bits):
 if e.tagged(v,'BYTE')and bits>=8:return v
 return texture.mask(v,bits)

def substitute(pattern,env):
 variable=atom(pattern)
 if variable is not None:
  assert variable in env,('unbound expression role',variable);return env[variable]
 if not isinstance(pattern,tuple):return pattern
 if pattern[0]=='LINEAR':
  value=pattern[1]
  for term,k in pattern[2]:value=e.add(value,e.scale(substitute(term,env),k))
  return value
 if pattern[0]in('AND','OR'):return e.bitop(pattern[0],substitute(pattern[1],env),substitute(pattern[2],env))
 if pattern[0]in('EQ','SLT','ULT'):return e.pred(pattern[0],substitute(pattern[1],env),substitute(pattern[2],env))
 if pattern[0]=='BOOL':return e.boolean(substitute(pattern[1],env))
 if pattern[0]=='NOT':return e.negate(substitute(pattern[1],env))
 if pattern[0]=='BYTE':return opening_byte(substitute(pattern[1],env),pattern[2])
 return tuple(substitute(value,env)if isinstance(value,tuple)else value for value in pattern)

opening_byte=p.opening.byte

def unify(pattern,actual,env,equations,where):
 assert not any(e.has_tag(v,tag)for v in(pattern,actual)for tag in('DEAD','DEAD_FP','PRIVATE_BYTE')),('undefined cut input',where,pattern,actual)
 variable=atom(pattern)
 if variable is not None:
  if variable in env:assert env[variable]==actual,('inconsistent role',where,variable,env[variable],actual)
  else:env[variable]=actual
  return
 if e.tagged(pattern,'AND')and pattern[2]in(255,65535)and atom(pattern[1])is not None:
  variable=atom(pattern[1]);bits=8 if pattern[2]==255 else 16
  if variable not in env:
   assert narrow(actual,bits)==actual,('unproved narrowed input',where,actual,bits);env[variable]=actual
  else:assert narrow(env[variable],bits)==actual,('narrowed input',where,env[variable],actual)
  return
 if isinstance(pattern,tuple):equations.append((pattern,actual,where))
 else:assert pattern==actual,('fixed cut value',where,pattern,actual)

def seed_initial(side):
 s=p.initial(side,'seed');s.r[2]=('OUTPUT_AFTER_SETUP',);s.r[16]=('STACK',-93)
 s.store(('STACK',-93),1,e.bitop('AND',('DIRTY',),255));s.private_writes=[];return s
def pair_initial(side):
 s=p.geometry_initial(side,'first-pair');s.f[6]=('A_X',)
 for reg,label in((18,'OFFSET_X'),(20,'OFFSET_Y'),(22,'OFFSET_Z')):s.f[reg]=(label,)
 return s
def loop_initial(side):
 s=p.geometry_initial(side,'loop-geometry');s.f[8]=('B_X',);s.r[7]=255;return s

def observe_cut(s,end):
 name=s.phase
 if name in('prefix','forward','backward'):return p.relation(s,end)
 p.saved(s)if name!='epilogue'else None
 if name=='setup':
  assert s.r[16]==('STACK',-93)
  return p.observations(s),s.r[2],s.r[17:22],s.load(('STACK',-4),4,b''),s.load(('STACK',-93),1,b'')
 if name=='epilogue':
  assert s.r[2]==p.OUTPUT and s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and tuple(s.f[20:])==tuple(('ENTRY_FP',i)for i in range(20,32))
  return p.observations(s),s.r[2]
 p.preserved_fp(s)
 if name=='seed':
  return p.observations(s),p.geometry_live(s),tuple(s.f[i]for i in(18,20,22,6)),s.r[5],s.f[30]
 if name=='first-pair':return p.observations(s),p.geometry_live(s),s.f[8],s.r[7],s.f[30]
 if name=='loop-geometry':return p.observations(s),p.geometry_live(s),tuple(s.f[i]for i in(18,20,22,4)),tuple(s.r[i]for i in(1,2,3,4,5,6,7)),s.f[30]
 if name=='second-pair':return p.observations(s),p.geometry_live(s),s.r[1],s.r[6],s.r[7],s.f[30]
 if name=='seam':return p.observations(s),p.geometry_live(s),s.r[7],s.f[30]
 if name=='tail':return p.observations(s),(s.r[16],)if end=='epilogue'else(p.geometry_live(s),s.f[8],s.r[7],s.f[30])
 raise AssertionError(name)

def specs():
 result=[]
 for name in('prefix','forward','backward'):
  result.append(dict(name=name,init=lambda side,n=name:p.initial(side,n),start=lambda side,n=name:0 if n=='prefix'else next(at for at,label in p.CUTS[side].items()if label==n),stop=lambda side:p.CUTS[side],next=lambda end:['setup'if end=='graphics'else end]))
 for name,init,start,stops in(
  ('setup',lambda side:p.initial(side,'setup'),lambda side:next(at for at,label in p.CUTS[side].items()if label=='graphics'),{0x298:'seed'}),
  ('seed',seed_initial,0x298,{0x4C4:'first-pair'}),
  ('first-pair',pair_initial,0x4C4,{0x5FC:'loop-geometry'}),
  ('loop-geometry',loop_initial,0x5FC,{0x6E8:'second-pair'}),
  ('second-pair',p.second_pair_initial,0x6E8,{0x860:'seam'}),
  ('seam',p.seam_initial,0x860,{0x8CC:'tail'}),
  ('tail',p.tail_initial,0x8CC,{0x5FC:'loop-geometry',0x96C:'epilogue'}),
  ('epilogue',lambda side:p.geometry_initial(side,'epilogue'),0x96C,{-4:'returned'})):
  result.append(dict(name=name,init=init,start=start if callable(start)else lambda side,n=start:n,stop=lambda side,st=stops:st,next=lambda end:[]if end=='returned'else[end]))
 return result

def prove(raw,retail,change=None,abi_fp=None):
 abi_fp={target:()for target in COUNTS}if abi_fp is None else abi_fp
 assert set(abi_fp)==set(COUNTS)and all(all(i in(12,13,14,15)for i in lanes)for lanes in abi_fp.values())
 models={};details=[];coverage={side:set()for side in('raw','retail')}
 for spec in specs():
  model=dict(spec=spec,initial={},states={},needed={});terms=Terms();outputs=[]
  for side,words in(('raw',raw),('retail',retail)):
   initial=spec['init'](side)
   if change:change(spec['name'],side,initial);initial.private_writes=[]
   model['initial'][side]=deepcopy(initial)
   paths,seen=run(p.Program(words,terms),spec['start'](side),spec['stop'](side),initial,abi_fp)
   coverage[side].update(seen)
   values={key:observe(state,lambda q,k=key:observe_cut(q,k[0]))for key,state in paths.items()}
   outputs.append(values);model['states'][side]=paths;model['needed'][side]=set.union(*(s.audit_needs for s in paths.values()))
  assert outputs[0]==outputs[1],('component transfer',spec['name'])
  models[spec['name']]=model
 # Propagate successor requirements backward across any path that leaves the
 # location untouched. This fixed point closes volatile-register and private
 # byte custody through components that neither read nor redefine a live value.
 rounds=0;added=0
 while True:
  changed=False;rounds+=1;assert rounds<100
  for name,model in models.items():
   for key in model['states']['raw']:
    for nxt in model['spec']['next'](key[0]):
     other=models[nxt]
     for side in('raw','retail'):
      source=model['states'][side][key]
      for loc in list(other['needed'][side]):
       kind=loc[0]
       if kind=='GPR':defined=loc[1]in source.audit_g or loc[1]==0
       elif kind=='FPR':defined=loc[1]in source.audit_f
       elif kind=='MEM':
        marks=[loc[1]+i in source.audit_mem for i in range(loc[2])]
        assert not any(marks)or all(marks),('partial private custody',name,nxt,side,loc)
        defined=all(marks)
       else:defined=kind in source.audit_special
       if not defined and loc not in model['needed'][side]:model['needed'][side].add(loc);changed=True;added+=1
  if not changed:break
 root=models['prefix']
 for side in('raw','retail'):
  for loc in root['needed'][side]:
   value_at_entry=value(root['initial'][side],loc)
   assert not any(e.has_tag(value_at_entry,tag)for tag in('DEAD','DEAD_FP','DEAD_HI','DEAD_LO','PRIVATE_BYTE')),('undefined function input',side,loc,value_at_entry)
 for name,model in models.items():
  for key in model['states']['raw']:
   successors=model['spec']['next'](key[0])
   if not successors:details.append(dict(component=name,end=key[0],terminal=True));continue
   matches=[];failures=[]
   for nxt in successors:
    other=models[nxt];env={};equations=[]
    try:
     for side in('raw','retail'):
      source=model['states'][side][key]
      for location in sorted(other['needed'][side],key=repr):unify(value(other['initial'][side],location),value(source,location),env,equations,(name,nxt,side,location))
     for pattern,actual,where in equations:assert substitute(pattern,env)==actual,('computed cut input',where,pattern,substitute(pattern,env),actual)
    except AssertionError as error:failures.append(str(error)[:1800])
    else:matches.append((nxt,len(env)))
   assert len(matches)==1,('cut composition',name,key[0],len(matches),failures)
   details.append(dict(component=name,end=key[0],successor=matches[0][0],roles=matches[0][1]))
 for side,words in(('raw',raw),('retail',retail)):assert coverage[side]==static(words),('reachable CFG',side,sorted(static(words)-coverage[side]),sorted(coverage[side]-static(words)))
 return dict(component_paths=len(details),edges=details,coverage={side:len(v)for side,v in coverage.items()},actual_cut_inputs_composed=True,transitive_custody_rounds=rounds,propagated_live_locations=added,complete_reachable_CFG=True,all_provider_ABI_register_and_sync_inputs_checked=True,explicit_saved_state_custody=True,whole_function=True,source_installed=False,c_match_credit=0)

if __name__=='__main__':
 raw,retail=p.programs(sys.argv[1]if len(sys.argv)>1 else'v7');report=prove(raw,retail)
 (O/'composition-v7.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='edges'}),flush=True)
