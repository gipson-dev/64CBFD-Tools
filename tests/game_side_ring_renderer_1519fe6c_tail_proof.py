"""Symbolic lookahead/zero-normalization and final ABI restoration."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

class State(texture.State):
 def __init__(self,side,high):
  super().__init__(side);self.phase='tail';self.r[6]=255
  self.r[7 if side=='raw'else 8]=('NEXT_INDEX',);self.r[8 if side=='raw'else 4]=('PREVIOUS_INDEX',)
  self.r[9 if side=='raw'else 7]=('TAG',);self.r[11]=texture.mask(('ALPHA',),8) if side=='raw'else ('ALPHA',)
  self.r[25 if side=='raw'else 15]=('STACK',-24)
  self.r[10 if side=='raw'else 9]=('STACK',-92+2*(2-high))
  if side=='raw':
   self.store(('STACK',-148),4,('STACK',-92+2*high));self.r[12]=0x0100600C;self.r[13]=0x05000608;self.r[31]=0x05000802
  else:self.r[13]=('STACK',-92+2*high);self.r[31]=0x0100600C
  for off in(-92,-90,-88):self.store(('STACK',off),2,('LOAD',('TEXTURE',off),2,0))
  self.fcsr=('FCSR','tail');self.private_writes=[]

def relation(s,high,end):
 opening.saved(s)
 assert all(size==4 and off in range(-36,-12,4) for off,size in s.private_writes),('lookahead private write escape',s.side,s.private_writes)
 accesses=set(event for event in s.trace if event[0]=='READ');effects=[event for event in s.trace if event[0]!='READ']
 assert all(event[0]=='FP' for event in effects),('unexpected lookahead public mutation',effects)
 if end=='return':live=(s.r[16],)
 else:
  assert (s.load(('STACK',-148),4,b'') if s.side=='raw'else s.r[13])==('STACK',-92+2*high)
  assert s.r[10 if s.side=='raw'else 9]==('STACK',-92+2*(2-high))
  assert s.r[12 if s.side=='raw'else 31]==0x0100600C and s.r[6]==255
  assert s.r[19 if s.side=='raw'else 18]==36
  if s.side=='raw':assert s.r[31]==0x05000802 and s.r[13]==0x05000608,('lookahead triangle constants',s.r[31],s.r[13])
  live=(s.r[16],s.r[17],s.r[7 if s.side=='raw'else 8],s.r[9 if s.side=='raw'else 7],texture.mask(s.r[11],8),tuple(s.f[i] for i in(8,14,16,18,20,22)),tuple(s.f[24:]),s.load(('STACK',-4),4,b''),tuple(s.load(('STACK',off),4,b'') for off in range(-36,-12,4)),s.r[18] if s.side=='raw'else s.r[12])
 return accesses,effects,s.fp,s.fcsr,live

def prove(raw,retail):
 terms=Terms();count=0
 for high in(0,2):
  results={}
  for side,words,start,stops in(('raw',raw,0x8F4,{0x6A8:'segment',0x9CC:'return'}),('retail',retail,0x8E4,{0x68C:'segment',0x9BC:'return'})):
   paths=texture.Program(words,terms).paths(start,stops,State(side,high));results[side]={key:relation(s,high,key[0]) for key,s in paths.items()}
  a,b=results['raw'],results['retail'];assert a.keys()==b.keys(),('lookahead predicates',len(a),len(b),next(iter(a.keys()-b.keys()),None),next(iter(b.keys()-a.keys()),None))
  for key in a:assert a[key]==b[key],('lookahead transfer',high,key,a[key],b[key])
  count+=len(a)
 returns={}
 for side,words,start in(('raw',raw,0x9CC),('retail',retail,0x9BC)):
  s=opening.initial(side,'return');s.fcsr=('FCSR','return');s.r[31]=('DIRTY_RA',side)
  for i in range(20,24):s.f[i]=('DIRTY_FP',side,i)
  paths=opening.Program(words).paths(start,{-4:'return'},s);assert len(paths)==1
  q=next(iter(paths.values()));assert q.r[2]==('OUTPUT',) and q.r[29]==('STACK',0) and q.r[31]==('RETURN',)
  assert not q.trace and not q.private_writes
  assert all(q.r[i]==('ENTRY',i) for i in(16,17,18,19,20,21,22,23,28,30)),('return saved GPR',q.r[16:24])
  assert tuple(q.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32));returns[side]=(q.r[2],q.fcsr)
 assert returns['raw']==returns['retail']
 return dict(symbolic_paths=count,return_paths=1,inductive_lookahead_and_repeat=True,exact_zero_predicate_separate_from_initial_epsilon=True,ordered_FP_FCSR_and_late_width_load=True,branch_likely_update=True,complete_saved_GPR_FPR_and_return=True,raw_fault_state_claimed=False,whole_function=False,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 for name,pc,change in(
  ('head-field',0x8F4,lambda w:w+1),
  ('lookahead-height-field',0x930,lambda w:w-4),
  ('lookahead-alpha-scale',0x978,lambda w:w^(1<<6)),
  ('exact-zero-compare',0x944,lambda w:w^14),
  ('late-width-field',0x9BC,lambda w:w+4),
  ('repeat-delay-annul',0x9C4,lambda w:w^(16<<26)),
  ('saved-register-restore',0x9E4,lambda w:w+4)):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),('invalid tail control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective tail control',name))
 report['effective_controls']=controls;out=g.O;(out/'tail-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
