"""One-segment transfer with arbitrary loop state and public aliases."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

class State(texture.State):
 def __init__(self,side,high):
  super().__init__(side);self.phase='segment';self.r[6]=255
  self.r[7 if side=='raw'else 8]=('INDEX',)
  self.r[9 if side=='raw'else 7]=('TAG',);self.r[11]=texture.mask(('ALPHA',),8) if side=='raw'else ('ALPHA',)
  self.r[10 if side=='raw'else 9]=('STACK',-92+2*(2-high))
  if side=='raw':
   self.store(('STACK',-148),4,('STACK',-92+2*high));self.r[12]=0x0100600C;self.r[13]=0x05000608;self.r[31]=0x05000802
  else:self.r[13]=('STACK',-92+2*high);self.r[31]=0x0100600C
  for off in(-92,-90,-88):self.store(('STACK',off),2,('LOAD',('TEXTURE',off),2,0))
  self.f[8]=('NEG_DZ',);self.fcsr=('FCSR','segment');self.private_writes=[]

def relation(s,high):
 opening.saved(s)
 assert all(size==4 and off==-4 for off,size in s.private_writes),('segment private write escape',s.side,s.private_writes)
 assert s.load(('STACK',-4),4,b'')==e.add(('VERTICES',),48),('segment vertex cursor',s.load(('STACK',-4),4,b''))
 assert s.r[16]==e.add(('OUTPUT',),40)
 assert s.r[25 if s.side=='raw'else 15]==('STACK',-24),('lookahead point pointer',s.r[25 if s.side=='raw'else 15])
 assert (s.load(('STACK',-148),4,b'') if s.side=='raw'else s.r[13])==('STACK',-92+2*high)
 assert s.r[10 if s.side=='raw'else 9]==('STACK',-92+2*(2-high))
 assert s.r[12 if s.side=='raw'else 31]==0x0100600C and s.r[6]==255
 assert s.r[19 if s.side=='raw'else 18]==36
 if s.side=='raw':assert s.r[31]==0x05000802 and s.r[13]==0x05000608,('segment triangle constants',s.r[31],s.r[13])
 writes=[event for event in s.trace if event[0]=='WRITE'];assert len(writes)==40
 live=(s.r[16],s.r[17],s.r[7 if s.side=='raw'else 8],s.r[8 if s.side=='raw'else 4],s.r[9 if s.side=='raw'else 7],texture.mask(s.r[11],8),tuple(s.f[i] for i in(14,16,18,20,22)),tuple(s.f[24:]),s.load(('STACK',-4),4,b''),tuple(s.load(('STACK',off),4,b'') for off in range(-36,-12,4)),s.r[18] if s.side=='raw'else s.r[12])
 return s.trace,s.fp,s.fcsr,live

def prove(raw,retail):
 terms=Terms();count=0
 for high in(0,2):
  results={}
  for side,words,start,stop in(('raw',raw,0x6A8,0x8F4),('retail',retail,0x68C,0x8E4)):
   paths=texture.Program(words,terms).paths(start,{stop:'lookahead'},State(side,high))
   results[side]={key:relation(state,high) for key,state in paths.items()}
  a,b=results['raw'],results['retail'];assert a.keys()==b.keys(),('segment predicates',high,a.keys(),b.keys())
  for key in a:
   if a[key]!=b[key]:
    mismatch=next((i for i,(x,y) in enumerate(zip(a[key][0],b[key][0])) if x!=y),None)
    raise AssertionError(('segment transfer',high,key,'event',mismatch,a[key][0][mismatch] if mismatch is not None else a[key],b[key][0][mismatch] if mismatch is not None else b[key]))
  count+=len(a)
 return dict(symbolic_paths=count,arbitrary_inductive_loop_state=True,vertices_per_segment=3,complete_vertex_and_command_writes=40,triangle_commands=4,all_output_aliases=True,ordered_public_and_FP_FCSR_effects=True,lookahead_and_return_proved=False,whole_function=False,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 for name,pc,change in(
  ('current-tag-offset',0x718,lambda w:w+2),
  ('center-opacity',0x7D4,lambda w:w&~(31<<16)),
  ('vertex-stride',0x878,lambda w:w+16),
  ('vertex-command-word',0x880,lambda w:w^(1<<16)),
  ('vertex-command-pointer',0x890,lambda w:w+16),
  ('triangle-final-indices',0x8D4,lambda w:w^2),
  ('index-decrement',0x6BC,lambda w:w-1),
  ('wrap-capacity',0x8EC,lambda w:w+1),
  ('lookahead-point-pointer',0x8E8,lambda w:w+4)):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),('invalid segment control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective segment control',name))
 report['effective_controls']=controls;out=g.O;(out/'segment-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
