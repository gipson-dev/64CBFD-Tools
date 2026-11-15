"""Instruction-driven six-provider setup transfer; geometry remains open."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g

class Program(opening.Program):
 def step(self,s,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==0 and fn==37 and (s.r[rs]==0 or s.r[rt]==0) and (e.tagged(s.r[rs],'STACK') or e.tagged(s.r[rt],'STACK')):
   s.r[rd]=s.r[rs] if s.r[rt]==0 else s.r[rt];s.r[0]=0
  else:super().step(s,w)
 def call(self,s,target):
  assert target in (g.TEXTURE,g.GEOMETRY,g.ENV,g.PRIM,g.COMBINE,g.MODE)
  n=g.COUNTS[target];args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4,b'') for i in range(max(0,n-4)))
  if target in g.SYNC:assert args[g.SYNC[target]]==('STACK',-95),('setup sync pointer',target,args)
  for i,a in enumerate(args):
   if target not in g.SYNC or i!=g.SYNC[target]:e.plain(a)
  ordinal=s.calls[target];s.calls[target]+=1
  s.trace.append(('CALL',target,args,s.fcsr));s.epoch+=1
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
  for i in range(4):s.store(('STACK',-240+4*i),4,('CALL_HOME',target,ordinal,i))
  if target in g.SYNC:s.store(('STACK',-95),1,('SYNC_AFTER',target,ordinal))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',target,ordinal)
  s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)

def relation(s):
 opening.saved(s)
 allowed=set(range(-240,-196,4))|{-8,-12,-95}
 assert all(off in allowed and size==(1 if off==-95 else 4) for off,size in s.private_writes),('setup private write escape',s.private_writes)
 assert s.r[19 if s.side=='raw'else 18]==36
 assert all(s.calls[t]==1 for t in(g.TEXTURE,g.GEOMETRY,g.ENV,g.PRIM,g.COMBINE,g.MODE))
 return(s.trace,s.r[2],s.r[16],s.r[17],s.load(('STACK',-4),4,b''),s.load(('STACK',-95),1,b''),s.load(('STACK',-8),4,b''),s.r[18] if s.side=='raw'else s.load(('STACK',-12),4,b''),s.fcsr,tuple(s.f[20:]),s.epoch)

def prove(raw,retail):
 results={}
 for side,words,start,stop in(('raw',raw,0x194,0x274),('retail',retail,0x18C,0x270)):
  s=opening.initial(side,'setup');s.phase='setup'
  paths=Program(words).paths(start,{stop:'seed'},s);assert len(paths)==1
  results[side]={key:relation(state) for key,state in paths.items()}
 assert results['raw']==results['retail'],('setup transfer',results)
 return dict(symbolic_paths=1,opaque_graphics_providers=6,all_provider_arguments_and_order=True,captured_packet_and_entries_retained=True,sync_home=-95,arbitrary_provider_public_mutations_and_FCSR=True,saved_GPR_FPR_and_private_inventory=True,geometry_proved=False,whole_function=False,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 alternative=raw[:]
 for pc in range(0x194,0x274,4):
  w=alternative[pc//4];op,fn=w>>26,w&63
  fields=() if op==3 else (16,) if op==15 else (21,16,11) if op==0 else (21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(14,15):w=(w&~(31<<shift))|((29-reg)<<shift)
  alternative[pc//4]=w
 assert alternative!=raw and prove(alternative,retail)==report
 report['independent_scratch_allocation_positive_control']=True
 for name,pc,change in(
  ('texture-index',0x198,lambda w:w-1),
  ('exposed-sync-home',0x19C,lambda w:w+1),
  ('red-channel-offset',0x1F8,lambda w:w+1),
  ('combine-mode',0x240,lambda w:w+1),
  ('render-mode-bits',0x260,lambda w:w^1),
  ('captured-packet-slot',0x1D0,lambda w:w-4)):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded proof','escaped code')),('invalid setup control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective setup control',name))
 report['effective_controls']=controls
 out=g.O;(out/'setup-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
