"""Whole-function cut composition audit, independent of any word projection."""
from copy import deepcopy
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_side_ring_renderer_1519fe6c_setup_proof as setup
from tools.tests import game_side_ring_renderer_1519fe6c_seed_proof as seed
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests import game_side_ring_renderer_1519fe6c_vertices_proof as vertices
from tools.tests import game_side_ring_renderer_1519fe6c_segment_proof as segment
from tools.tests import game_side_ring_renderer_1519fe6c_tail_proof as tail
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_side_ring_renderer_1519fe6c_coverage import static

def need(s,kind,index=None):
 if kind=='GPR' and index==0:return
 defined=s.audit_g if kind=='GPR'else s.audit_f if kind=='FPR'else s.audit_special
 if (index if index is not None else kind) not in defined:s.audit_needs.add((kind,) if index is None else(kind,index))

def writes(s,kind,indices):
 defined=s.audit_g if kind=='GPR'else s.audit_f if kind=='FPR'else s.audit_special
 defined.update(indices)

def decode(s,w):
 """Architectural operand reads, excluding implementation helper lookups."""
 if not w:return (),()
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 rg=[];rf=[];wg=[];wf=[];special=[];written=[]
 if op==0:
  if fn in(0,2,3):rg=[rt];wg=[rd]
  elif fn in(4,6,7,33,35,36,37,42,43):rg=[rs,rt];wg=[rd]
  elif fn in(16,18):special=['HI' if fn==16 else 'LO'];wg=[rd]
  elif fn in(24,25,26,27):rg=[rs,rt];written=['HI','LO']
  else:raise AssertionError(('unexpected tracked integer op',hex(w)))
 elif op in(9,10,11,12,13):rg=[rs];wg=[rt]
 elif op==15:wg=[rt]
 elif op in(32,33,35,36,37):rg=[rs];wg=[rt]
 elif op in(40,41,43):rg=[rs,rt]
 elif op in(49,53):rg=[rs];wf=list(range(rt,rt+(2 if op==53 else 1)))
 elif op in(57,61):rg=[rs];rf=list(range(rt,rt+(2 if op==61 else 1)))
 elif op==17:
  if rs==0:rf=[rd];wg=[rt]
  elif rs==4:rg=[rt];wf=[rd]
  elif rs==16:
   rf=[rd,rt] if fn in(0,1,2,3,50,60) else [rd]
   if fn!=6:special=['FCSR'];written=['FCSR']
   if fn in(50,60):written+=['COND']
   else:wf=[w>>6&31]
  else:raise AssertionError(('unexpected tracked FP op',hex(w)))
 else:raise AssertionError(('unexpected tracked opcode',hex(w)))
 for i in rg:need(s,'GPR',i)
 for i in rf:need(s,'FPR',i)
 for item in special:need(s,item)
 return (wg,wf),written

class ObservedList(list):
 def __init__(self,items,state,kind):super().__init__(items);self.state=state;self.kind=kind
 def __getitem__(self,index):
  if self.state.audit_observe:
   for i in range(*index.indices(len(self))) if isinstance(index,slice)else(index,):need(self.state,self.kind,i)
  return super().__getitem__(index)

def tracked(s):
 base=s.__class__
 class Tracked(base):
  def load(self,address,size,pool):
   if self.audit_active and e.tagged(address,'STACK'):
    existing=[address[1]+i in self.audit_mem for i in range(size)]
    assert not any(existing) or all(existing),('mixed initial private read',address,size)
    if not any(existing):self.audit_needs.add(('MEM',address[1],size))
   return super().load(address,size,pool)
  def store(self,address,size,value):
   result=super().store(address,size,value)
   if self.audit_active and e.tagged(address,'STACK'):self.audit_mem.update(range(address[1],address[1]+size))
   return result
 s.__class__=Tracked;s.audit_g=set();s.audit_f=set();s.audit_special=set();s.audit_mem=set();s.audit_needs=set();s.audit_observe=False;s.audit_active=True;s.audit_calls=[]
 return s

def run(program,start,stops,initial,abi_fp):
 answers={};states=[(start,tracked(initial))];work=0;fetched=set()
 def instruction(pc):fetched.add(pc);return program.instruction(pc)
 def step(s,w):
  dest,special=decode(s,w);program.step(s,w)
  if dest:
   writes(s,'GPR',dest[0]);writes(s,'FPR',dest[1])
  s.audit_special.update(special)
 while states:
  pc,s=states.pop();work+=1;s.steps+=1;assert work<20000 and s.steps<500,('composition bound',hex(pc))
  if s.steps>1 and pc in stops:
   if 'FCSR' not in s.audit_special:s.audit_needs.add(('FCSR',))
   key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers;answers[key]=s;continue
  w=instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
  if floating or op in(1,4,5,6,7,20,21,22,23):
   if floating:
    need(s,'COND');assert s.fp_condition is not None;condition=s.fp_condition
    if not rt&1:condition=e.negate(condition)
    likely=bool(rt&2)
   elif op==1:
    need(s,'GPR',rs);assert rt in(0,1,2,3);condition=e.pred('SLT',s.r[rs],0)
    if rt in(1,3):condition=e.negate(condition)
    likely=rt in(2,3)
   else:
    need(s,'GPR',rs)
    if op in(4,5,20,21):need(s,'GPR',rt);condition=e.pred('EQ',s.r[rs],s.r[rt])
    else:assert rt==0;condition=e.pred('SLT',0,s.r[rs])
    if op in(5,21,6,22):condition=e.negate(condition)
    likely=op>=20
   for take in e.choices(s,condition):
    q=deepcopy(s);e.assume(q,condition,take)
    if take or not likely:step(q,instruction(pc+4))
    target=pc+4+4*(((w&65535)^32768)-32768) if take else pc+8;states.append((target,q))
  elif op==3:
   s.r[31]=program.entry+pc+8;s.audit_g.add(31);step(s,instruction(pc+4));target=((program.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2)
   for i in range(4,4+min(g.COUNTS[target],4)):need(s,'GPR',i)
   assert target in abi_fp,('unclassified call ABI',target)
   for i in abi_fp[target]:need(s,'FPR',i)
   if abi_fp[target]:s.audit_calls.append((target,'FP_ARGS',tuple(s.f[i] for i in abi_fp[target])))
   need(s,'FCSR')
   if target in g.SYNC:s.audit_calls.append((target,s.load(('STACK',-95),1,b'')))
   program.call(s,target);s.audit_g.update((1,2,3,*range(4,16),24,25,31));s.audit_f.update(range(20));s.audit_special.update(('FCSR','HI','LO'));states.append((pc+8,s))
  elif op==0 and w&63==8:
   need(s,'GPR',rs);target=s.r[rs];step(s,instruction(pc+4));assert target==('RETURN',);states.append((-4,s))
  else:step(s,w);states.append((pc+4,s))
 return answers,fetched

def observe(s,fn):
 s.r=ObservedList(s.r,s,'GPR');s.f=ObservedList(s.f,s,'FPR');s.audit_observe=True
 value=fn(s)
 # Explicit custody: registers carried unchanged, plus every saved entry word.
 # Values intentionally overwritten before use do not need an incoming value.
 for i in(16,17,18,19,20,21,22,23,28,30):need(s,'GPR',i)
 for i in range(20,32):need(s,'FPR',i)
 if s.r[29]==('STACK',-240):
  opening.saved(s)
 s.audit_observe=False;s.audit_active=False
 if 'FCSR' not in s.audit_special:s.audit_needs.add(('FCSR',))
 return value,s.audit_calls

def value(s,loc):
 kind=loc[0]
 if kind=='GPR':return s.r[loc[1]]
 if kind=='FPR':return s.f[loc[1]]
 if kind=='MEM':return s.load(('STACK',loc[1]),loc[2],b'')
 return s.fcsr if kind=='FCSR'else s.hi if kind=='HI'else s.lo if kind=='LO'else s.fp_condition

def atom(v):
 if not isinstance(v,tuple):return None
 if len(v)==1 and v[0] not in('RETURN',):return v
 if v[0]=='FCSR':return ('FCSR',)
 if v[0]=='LOAD' and e.tagged(v[1],'TEXTURE'):return ('TEXTURE',v[1][1])
 return None

def unify(pattern,actual,env,constraints,where):
 assert not any(e.has_tag(v,tag) for v in(pattern,actual) for tag in('DEAD','DEAD_FP','PRIVATE_BYTE')),('undefined cut input',where,pattern,actual)
 variable=atom(pattern)
 if variable is not None:
  assert not any(e.has_tag(actual,tag) for tag in('DEAD','DEAD_FP','PRIVATE_BYTE')),('unmodelled predecessor input',where,pattern,actual)
  if variable[0]=='TEXTURE':assert texture.mask(actual,16)==actual,('non-halfword texture input',where,actual)
  if variable in env:assert env[variable]==actual,('inconsistent cut input',where,variable,env[variable],actual)
  else:env[variable]=actual
 elif e.tagged(pattern,'AND') and pattern[2] in(255,65535) and atom(pattern[1]) is not None:
  constraints.append((atom(pattern[1]),8 if pattern[2]==255 else 16,actual,where))
 else:assert pattern==actual,('fixed cut input',where,pattern,actual)

def specs():
 result=[]
 for label in('prefix','forward','backward'):
  result.append(dict(name=label,kind=opening.Program,init=lambda side,l=label:opening.initial(side,l),start=lambda side,l=label:0 if l=='prefix'else next(pc for pc,v in opening.CUTS[side].items() if v==l),stop=lambda side:opening.CUTS[side],observe=lambda s,end:opening.relation(s,end),next=lambda end,l=label:[] if end=='return'else['setup' if end=='graphics'else end]))
 result += [dict(name='setup',kind=setup.Program,init=lambda side:opening.initial(side,'setup'),start=lambda side:0x194 if side=='raw'else 0x18C,stop=lambda side:{0x274 if side=='raw'else 0x270:'seed'},observe=lambda s,end:setup.relation(s),next=lambda end:['seed']),dict(name='seed',kind=seed.Program,init=seed.State,start=lambda side:0x274 if side=='raw'else 0x270,stop=lambda side:{0x430 if side=='raw'else 0x42C:'texture'},observe=lambda s,end:seed.relation(s),next=lambda end:['texture']),dict(name='texture',kind=texture.Program,init=texture.State,start=lambda side:0x430 if side=='raw'else 0x42C,stop=lambda side:{0x4F0 if side=='raw'else 0x4E8:'vertices'},observe=lambda s,end:texture.relation(s),next=lambda end:['vertices-0','vertices-2'])]
 for high in(0,2):
  result += [dict(name='vertices-'+str(high),kind=texture.Program,init=lambda side,h=high:vertices.State(side,h),start=lambda side:0x4F0 if side=='raw'else 0x4E8,stop=lambda side:{0x6A8 if side=='raw'else 0x68C:'segment'},observe=lambda s,end,h=high:vertices.relation(s,h),next=lambda end,h=high:['segment-'+str(h)]),dict(name='segment-'+str(high),kind=texture.Program,init=lambda side,h=high:segment.State(side,h),start=lambda side:0x6A8 if side=='raw'else 0x68C,stop=lambda side:{0x8F4 if side=='raw'else 0x8E4:'tail'},observe=lambda s,end,h=high:segment.relation(s,h),next=lambda end,h=high:['tail-'+str(h)]),dict(name='tail-'+str(high),kind=texture.Program,init=lambda side,h=high:tail.State(side,h),start=lambda side:0x8F4 if side=='raw'else 0x8E4,stop=lambda side:{0x6A8 if side=='raw'else 0x68C:'segment',0x9CC if side=='raw'else 0x9BC:'return'},observe=lambda s,end,h=high:tail.relation(s,h,end),next=lambda end,h=high:['return'] if end=='return'else['segment-'+str(h)])]
 def returned(s,end):
  assert s.r[2]==('OUTPUT',) and s.r[29]==('STACK',0) and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i) for i in(16,17,18,19,20,21,22,23,28,30));assert tuple(s.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32));return s.trace,s.fcsr
 result.append(dict(name='return',kind=opening.Program,init=lambda side:opening.initial(side,'return'),start=lambda side:0x9CC if side=='raw'else 0x9BC,stop=lambda side:{-4:'return'},observe=returned,next=lambda end:[]))
 return result

def prove(raw,retail,change=None,abi_fp=None):
 # All seven recovered call declarations have pointer/integer register args.
 # An explicit map prevents silently assuming that a new provider has no FP args.
 declared={g.BACKEND:5,g.TEXTURE:11,g.GEOMETRY:3,g.ENV:6,g.PRIM:8,g.COMBINE:3,g.MODE:4}
 assert g.COUNTS==declared,('unclassified renderer call signature',g.COUNTS)
 abi_fp={target:() for target in declared} if abi_fp is None else abi_fp
 assert set(abi_fp)==set(g.COUNTS) and all(all(i in(12,13,14,15) for i in lanes) for lanes in abi_fp.values())
 models={};details=[];coverage={'raw':set(),'retail':set()}
 for spec in specs():
  model=dict(spec=spec,initial={},states={},needed={});terms=Terms()
  for side,words in(('raw',raw),('retail',retail)):
   initial=spec['init'](side)
   if change is not None:change(spec['name'],side,initial);initial.private_writes=[]
   model['initial'][side]=deepcopy(initial)
   program=spec['kind'](words) if spec['kind'] in(opening.Program,setup.Program)else spec['kind'](words,terms)
   paths,seen=run(program,spec['start'](side),spec['stop'](side),initial,abi_fp);coverage[side].update(seen)
   outputs={key:observe(s,lambda q,k=key:spec['observe'](q,k[0])) for key,s in paths.items()}
   model['states'][side]=paths;model['needed'][side]=set.union(*(s.audit_needs for s in paths.values()))
   if side=='raw':left=outputs
   else:assert left==outputs,('component under composition runner',spec['name'])
  models[spec['name']]=model
 for name,model in models.items():
  for key in model['states']['raw']:
   successors=model['spec']['next'](key[0])
   if not successors:details.append(dict(component=name,end=key[0],terminal=True));continue
   matches=[];failures=[]
   for nxt in successors:
    next_model=models[nxt];env={};constraints=[]
    try:
     for side in('raw','retail'):
      source=model['states'][side][key]
      for loc in sorted(next_model['needed'][side],key=repr):unify(value(next_model['initial'][side],loc),value(source,loc),env,constraints,(name,nxt,side,loc))
     for variable,bits,actual,where in constraints:
      assert variable in env,('unbound narrowed role',where,variable)
      assert texture.mask(env[variable],bits)==actual,('narrowed cut input',where,variable,env[variable],actual)
    except AssertionError as error:failures.append(str(error)[:1200])
    else:matches.append((nxt,len(env),len(constraints)))
   assert len(matches)==1,('cut composition',name,key[0],len(matches),failures)
   details.append(dict(component=name,end=key[0],successor=matches[0][0],shared_roles=matches[0][1],narrowed_roles=matches[0][2]))
 for side,words in (('raw',raw),('retail',retail)):
  assert coverage[side]==static(words),('incomplete reachable CFG',side,sorted(static(words)-coverage[side]),sorted(coverage[side]-static(words)))
 return dict(component_paths=len(details),edges=details,coverage={k:len(v) for k,v in coverage.items()},unreachable_offsets={side:[hex(pc) for pc in range(0,4*len(words),4) if pc not in coverage[side]] for side,words in (('raw',raw),('retail',retail))},actual_cut_inputs_composed=True,complete_reachable_CFG=True,opaque_exposed_sync_inputs_compared=True,explicit_saved_state_custody=True,whole_function=True,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 def renamed(name,side,s):
  if name=='texture':s.r[11]=texture.mask(('RENAMED_ALPHA',),8) if side=='raw'else ('RENAMED_ALPHA',)
 assert prove(raw,retail,renamed)==report
 dead=raw[:];dead[0x2F4//4]+=1;assert prove(dead,retail)==report
 for label in('setup-sync','vertex-texture','segment-position','lookahead-pointer','return-FCSR','forward-count','preserved-FPR-entry','call-FPR-entry'):
  def change(name,side,s):
   if label=='setup-sync' and name=='setup':s.store(('STACK',-95),1,0)
   if label=='vertex-texture' and name.startswith('vertices-'):s.store(('STACK',-92),2,0)
   if label=='segment-position' and name.startswith('segment-'):s.store(('STACK',-24),4,0)
   if label=='lookahead-pointer' and name.startswith('tail-'):s.r[25 if side=='raw'else 15]=('STACK',-36)
   if label=='return-FCSR' and name=='return':s.fcsr=0
   if label=='forward-count' and name=='forward':s.r[4]=0
   if label=='preserved-FPR-entry' and name=='seed':s.f[24]=0
   if label=='call-FPR-entry' and name=='setup':s.f[12]=0
  abi_fp={target:(12,) if target==g.TEXTURE and label=='call-FPR-entry' else() for target in g.COUNTS}
  try:prove(raw,retail,change,abi_fp)
  except AssertionError as error:
   reason=str(error);assert 'cut composition' in reason,('control did not reach composition',label,reason[:500]);controls.append(dict(name=label,rejected=reason[:250]))
  else:raise AssertionError(('ineffective composition control',label))
 report['independent_input_role_rename_positive_control']=True;report['unreachable_word_semantics_positive_control']=True;report['effective_cut_controls']=controls
 out=g.O;(out/'composition-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='edges'}),flush=True)
if __name__=='__main__':main()
