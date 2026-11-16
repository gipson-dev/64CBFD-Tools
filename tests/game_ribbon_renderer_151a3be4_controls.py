"""Effective instruction/input controls independent of any target hash guard."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests import game_ribbon_renderer_151a3be4_composition as c
O=c.O
p=c.p;e=p.e

def main():
 raw,retail=p.programs('v7');baseline=c.prove(raw,retail);word_controls=[];cut_controls=[]
 for label,at,mask,check in(
  ('backend-allocation-size',0x78,16,p.opening_proof),
  ('fade-step-byte',0xFC,1,p.opening_proof),
  ('texture-index',0x1C8,1,p.setup_proof),
  ('combine-index',0x264,1,p.setup_proof),
  ('initial-position-z',0x3E0,4,p.seed_proof),
  ('normal-length-add',0x474,1,p.seed_proof),
  ('initial-vertex-y',0x4FC,2,p.first_pair_proof),
  ('loop-camera-z',0x618,4,p.loop_geometry_proof),
  ('seam-copy-length',0x63C,1,p.loop_geometry_proof),
  ('vertex-red-byte',0x750,1,p.second_pair_proof),
  ('first-triangle-index',0x838,2,p.second_pair_proof),
  ('seam-source-write',0x89C,2,p.seam_proof),
  ('tail-lifetime-source',0x934,2,p.tail_proof),
  ('return-cursor',0x96C,1<<21,lambda a,b:p.epilogue_proof(a,b,False)),
  ('saved-F30-pair',0x988,8,lambda a,b:p.epilogue_proof(a,b,False))):
  bad=raw.copy();bad[at//4]^=mask
  try:check(bad,retail)
  except AssertionError as error:
   reason=str(error);assert reason and not any(tag in reason for tag in('unsupported','unbounded','escaped code','uninitialized private read')),('invalid word control',label,reason)
   word_controls.append(dict(label=label,offset=hex(at),rejected=True,reason=reason[:450]));print(label,'rejected',flush=True)
  else:raise AssertionError(('ineffective word control',label))
 for label in('setup-sync','initial-position','loop-x-livein','seam-predicate','seam-color','tail-lookahead','return-FCSR','forward-count','provider-FPR-argument'):
  def change(name,side,s):
   if label=='setup-sync'and name=='setup':s.store(('STACK',-93),1,0)
   if label=='initial-position'and name=='first-pair':s.store(('STACK',-80),4,0);s.f[6]=0
   if label=='loop-x-livein'and name=='loop-geometry':s.f[8]=0
   if label=='seam-predicate'and name=='seam':s.r[1]=0
   if label=='seam-color'and name=='seam':s.r[7]=0
   if label=='tail-lookahead'and name=='tail':s.r[12]=('STACK',-80)
   if label=='return-FCSR'and name=='epilogue':s.fcsr=0
   if label=='forward-count'and name=='forward':s.r[3 if side=='raw'else 4]=0
   if label=='provider-FPR-argument'and name=='setup':s.f[12]=0
  abi={target:(12,)if target==p.TEXTURE and label=='provider-FPR-argument'else()for target in p.COUNTS}
  try:c.prove(raw,retail,change,abi)
  except AssertionError as error:
   reason=str(error);assert 'cut composition'in reason,('cut control failed elsewhere',label,reason[:800])
   cut_controls.append(dict(label=label,rejected=True,reason=reason[:500]));print(label,'cut rejected',flush=True)
  else:raise AssertionError(('ineffective cut control',label))
 def rename(name,side,s):
  if name=='first-pair':s.f[18]=('RENAMED_OFFSET_X',)
 assert c.prove(raw,retail,rename)==baseline
 unreachable=raw.copy();unreachable[0x31C//4]^=1;assert c.prove(unreachable,retail)==baseline
 renamed=raw.copy();swap=lambda r:14 if r==13 else 13 if r==14 else r
 for i,w in enumerate(raw):
  op,fmt=w>>26,w>>21&31
  if op==17:fields=(16,)if fmt in(0,4)else()
  elif op in(2,3):fields=()
  elif op in(49,53,57,61):fields=(21,)
  elif op==0:fields=(21,16,11)
  else:fields=(21,16)
  for shift in fields:w=(w&~(31<<shift))|(swap(w>>shift&31)<<shift)
  renamed[i]=w
 assert renamed!=raw;assert c.prove(renamed,retail)==baseline
 report=dict(whole_composition=baseline,word_controls=word_controls,cut_controls=cut_controls,independent_role_rename_positive=True,temporary_GPR_rename_positive=True,unreachable_semantics_positive=True,source_installed=False,c_match_credit=0)
 (O/'whole-proof-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(words=len(word_controls),cuts=len(cut_controls),positive_controls=3,passes=True)),flush=True);return report

if __name__=='__main__':main()
