"""Initial three-vertex transfer; repeated segment loop stays open."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

class State(texture.State):
 def __init__(self,side,high):
  super().__init__(side);self.phase='vertices';self.r[2]=high;self.r[3]=2-high
  self.r[14 if side=='raw'else 25]=('VERTICES',)
  self.f[0]=('OFFSET_X',);self.f[6]=('FIRST_X_TRUNC',);self.f[12]=('PREVIOUS_WIDTH',)
  for off in(-92,-90,-88):self.store(('STACK',off),2,('LOAD',('TEXTURE',off),2,0))
  self.fcsr=('FCSR','vertices');self.private_writes=[]

def relation(s,high):
 opening.saved(s)
 assert all((size==4 and off==-4) or(s.side=='raw' and size==4 and off==-148) for off,size in s.private_writes),('vertices private write escape',s.side,s.private_writes)
 assert s.load(('STACK',-4),4,b'')==e.add(('VERTICES',),48)
 highptr=('STACK',-92+2*high);lowptr=('STACK',-92+2*(2-high))
 assert (s.load(('STACK',-148),4,b'') if s.side=='raw'else s.r[13])==highptr
 assert s.r[10 if s.side=='raw'else 9]==lowptr
 assert s.r[12 if s.side=='raw'else 31]==0x0100600C
 assert s.r[19 if s.side=='raw'else 18]==36
 assert s.r[6]==255,('vertex color constant',s.r[6])
 if s.side=='raw':assert s.r[31]==0x05000802 and s.r[13]==0x05000608
 effects=[event for event in s.trace if event[0]!='READ'];assert len([event for event in effects if event[0]=='WRITE'])==30
 live=(s.r[16],s.r[17],s.r[7 if s.side=='raw'else 8],s.r[9 if s.side=='raw'else 7],texture.mask(s.r[11],8),tuple(s.f[i] for i in(8,14,16,18,20,22)),tuple(s.f[24:]),s.load(('STACK',-4),4,b''),tuple(s.load(('STACK',off),4,b'') for off in range(-36,-12,4)),s.r[18] if s.side=='raw'else s.r[12])
 return effects,s.fp,s.fcsr,live

def prove(raw,retail):
 terms=Terms();count=0
 for high in(0,2):
  results={}
  for side,words,start,stop in(('raw',raw,0x4F0,0x6A8),('retail',retail,0x4E8,0x68C)):
   result=texture.Program(words,terms).paths(start,{stop:'segment'},State(side,high));assert len(result)==1
   results[side]={key:relation(state,high) for key,state in result.items()}
  a,b=results['raw'],results['retail'];assert a.keys()==b.keys()
  for key in a:
   if a[key]!=b[key]:
    mismatch=next((i for i,(x,y) in enumerate(zip(a[key][0],b[key][0])) if x!=y),None)
    raise AssertionError(('initial vertices transfer',high,'event',mismatch,a[key][0][mismatch] if mismatch is not None else a[key],b[key][0][mismatch] if mismatch is not None else b[key]))
  count+=len(a)
 return dict(symbolic_paths=count,initial_vertices=3,complete_public_vertex_writes=30,mode_orientations=2,ordered_FP_and_public_writes=True,arbitrary_FP_words_and_FCSR=True,texture_pointer_homes=dict(raw=-148,retail='T5'),repeated_segment_loop_proved=False,whole_function=False,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 for name,pc,change in(
  ('first-coordinate-offset',0x4FC,lambda w:w+2),
  ('texture-high-halfword',0x55C,lambda w:w+2),
  ('vertex-red-byte',0x568,lambda w:w&~(31<<16)),
  ('vertex-flag-halfword',0x588,lambda w:w+2),
  ('center-opacity-byte',0x60C,lambda w:w&~(31<<16)),
  ('high-texture-pointer-home',0x690,lambda w:w+4),
  ('ordered-FP-offset-multiply',0x510,lambda w:w^((4^12)<<11)^((4^12)<<16))):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),('invalid vertices control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective vertices control',name))
 report['early_byte_narrowing_vs_wide_input_relation']=True
 report['effective_controls']=controls;out=g.O;(out/'vertices-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
